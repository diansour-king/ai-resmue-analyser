import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, setColdStartListener } from "@/lib/api";

/**
 * The deployment runs the web app and the API as two separate free instances that sleep
 * when idle. A visitor's first request wakes the web app, whose proxy then reaches an API
 * that is still starting, and the gateway answers 502 before the API is listening.
 *
 * Retrying is only safe because those statuses mean the request never arrived. These tests
 * pin both halves of that contract: transient gateway failures are retried, and a real
 * application error is surfaced immediately rather than being retried into a long stall.
 */
const jsonResponse = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });

describe("cold-start handling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    setColdStartListener(null);
  });

  it("retries a 502 until the API finishes waking, then returns the real response", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(502, {}))
      .mockResolvedValueOnce(jsonResponse(502, {}))
      .mockResolvedValueOnce(jsonResponse(202, { sent: true, login_url: "/auth/verify?token=t" }));
    vi.stubGlobal("fetch", fetchMock);

    const promise = api.signUp("someone@example.com");
    await vi.runAllTimersAsync();

    await expect(promise).resolves.toEqual({ sent: true, login_url: "/auth/verify?token=t" });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("tells the UI it is waking, and that it has stopped, around a retry", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(503, {}))
      .mockResolvedValueOnce(jsonResponse(202, { sent: true, login_url: null }));
    vi.stubGlobal("fetch", fetchMock);

    const waking: boolean[] = [];
    setColdStartListener((v) => waking.push(v));

    const promise = api.signUp("someone@example.com");
    await vi.runAllTimersAsync();
    await promise;

    expect(waking).toEqual([true, false]);
  });

  it("retries a network failure, which is indistinguishable from a gateway that is not up", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(jsonResponse(202, { sent: true, login_url: null }));
    vi.stubGlobal("fetch", fetchMock);

    const promise = api.signUp("someone@example.com");
    await vi.runAllTimersAsync();

    await expect(promise).resolves.toEqual({ sent: true, login_url: null });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("does not retry an application error, which did reach the API", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(400, { error: { code: "invalid_link", message: "no" }, request_id: "r" }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const promise = api.verify("bad-token").catch((e: unknown) => e);
    await vi.runAllTimersAsync();
    const caught = await promise;

    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).code).toBe("invalid_link");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("gives up with a specific message rather than hanging forever", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(502, {}));
    vi.stubGlobal("fetch", fetchMock);

    const promise = api.signUp("someone@example.com").catch((e: unknown) => e);
    await vi.runAllTimersAsync();
    const caught = await promise;

    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).code).toBe("server_waking");
  });
});
