import type {
  Finding,
  Identity,
  Resume,
  ResumeSummary,
  Skill,
  UploadAccepted,
} from "./types";

/**
 * The only place in the app that talks to the network.
 *
 * Components never call fetch. They call these functions and get either a value or an
 * ApiError, so error handling is one shape everywhere and a change to the transport - a
 * header, a retry, a base path - happens once.
 */

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;

  constructor(status: number, code: string, message: string, requestId: string | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }

  get isUnauthenticated(): boolean {
    return this.status === 401;
  }
}

type ErrorEnvelope = { error?: { code?: string; message?: string }; request_id?: string };

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      // Same-origin: /v1 is proxied to the API by next.config.ts, which is what lets the
      // session cookie work without CORS and without the browser ever seeing the API host.
      credentials: "same-origin",
      headers: { Accept: "application/json", ...(init.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "network", "Could not reach CareerLayer. Check your connection.", null);
  }

  if (response.status === 204) return undefined as T;

  const requestId = response.headers.get("x-request-id");
  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const envelope = (body ?? {}) as ErrorEnvelope;
    throw new ApiError(
      response.status,
      envelope.error?.code ?? "error",
      envelope.error?.message ?? "Something went wrong.",
      envelope.request_id ?? requestId,
    );
  }
  return body as T;
}

function postJson<T>(path: string, payload: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export const api = {
  signUp: (email: string, displayName?: string) =>
    postJson<{ sent: boolean; login_url: string | null }>("/v1/auth/signup", {
      email,
      display_name: displayName ?? null,
    }),

  logIn: (email: string) =>
    postJson<{ sent: boolean; login_url: string | null }>("/v1/auth/login", { email }),

  verify: (token: string) => postJson<Identity>("/v1/auth/verify", { token }),

  logOut: () => request<void>("/v1/auth/logout", { method: "POST" }),

  me: () => request<Identity>("/v1/auth/me"),

  completeOnboarding: (displayName: string) =>
    postJson<Identity>("/v1/auth/onboarding", { display_name: displayName }),

  listResumes: () => request<ResumeSummary[]>("/v1/resumes"),

  getResume: (resumeId: string) => request<Resume>(`/v1/resumes/${resumeId}`),

  getFindings: (resumeId: string) => request<Finding[]>(`/v1/resumes/${resumeId}/findings`),

  getSkills: (resumeId: string) => request<Skill[]>(`/v1/resumes/${resumeId}/skills`),

  /**
   * The rendered page is fetched by URL, not by this client: it is an image the browser
   * loads into an <img>. It still travels through the API, so access is checked per request
   * and the browser never receives a storage credential.
   */
  pageRenderUrl: (resumeId: string, pageNumber: number) =>
    `/v1/resumes/${resumeId}/pages/${pageNumber}`,

  upload: (file: File, onProgress?: (fraction: number) => void) =>
    new Promise<UploadAccepted>((resolve, reject) => {
      // XMLHttpRequest rather than fetch, purely because it is the only browser API that
      // reports upload progress. The user needs to see a large PDF moving.
      const form = new FormData();
      form.append("file", file);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/v1/resumes");
      xhr.withCredentials = true;
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) onProgress(event.loaded / event.total);
      };
      xhr.onload = () => {
        let parsed: unknown = null;
        try {
          parsed = JSON.parse(xhr.responseText) as unknown;
        } catch {
          parsed = null;
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(parsed as UploadAccepted);
          return;
        }
        const envelope = (parsed ?? {}) as ErrorEnvelope;
        reject(
          new ApiError(
            xhr.status,
            envelope.error?.code ?? "error",
            envelope.error?.message ?? "The upload failed.",
            envelope.request_id ?? null,
          ),
        );
      };
      xhr.onerror = () =>
        reject(new ApiError(0, "network", "The upload could not reach CareerLayer.", null));
      xhr.send(form);
    }),
};
