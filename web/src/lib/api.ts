import type {
  Finding,
  GapAnalysisResponse,
  Identity,
  JobAccepted,
  JobDescription,
  JobRequirement,
  JobSummary,
  MatchAccepted,
  MatchRun,
  MatchSummary,
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

/**
 * Statuses that mean the request never reached the application.
 *
 * The deployment runs the web app and the API as two separate free instances, each of which
 * sleeps after ~15 minutes idle and takes up to a minute to wake. A visitor's first request
 * wakes the web app, whose proxy then hits an API that is still asleep, and the gateway
 * answers 502 before the API is listening. Retrying is safe precisely because the request
 * did not arrive: nothing was executed to be executed twice.
 */
const COLD_START_STATUS = new Set([502, 503, 504]);

/** Roughly 75s of patience, which covers a Render free instance cold start. */
const COLD_START_BACKOFF_MS = [1_000, 2_000, 4_000, 8_000, 10_000, 10_000, 10_000, 10_000, 10_000];

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Called when a request is being retried because the server appears to be waking up, so the
 * UI can say so rather than leaving a button spinning for a minute with no explanation.
 */
let onColdStart: ((waking: boolean) => void) | null = null;

export function setColdStartListener(listener: ((waking: boolean) => void) | null): void {
  onColdStart = listener;
}

/** Wake the API without blocking the caller. Fire this when an entry screen mounts so the
 *  instance is already listening by the time someone submits a form. */
export function warmUp(): void {
  void fetch("/v1/health", { method: "GET", cache: "no-store" }).catch(() => {});
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let notifiedColdStart = false;

  for (let attempt = 0; ; attempt += 1) {
    let response: Response | null = null;
    try {
      response = await fetch(path, {
        ...init,
        // Same-origin: /v1 is proxied to the API by next.config.ts, which is what lets the
        // session cookie work without CORS and without the browser ever seeing the API host.
        credentials: "same-origin",
        headers: { Accept: "application/json", ...(init.headers ?? {}) },
      });
    } catch {
      // A network-level failure is indistinguishable from a gateway that is not up yet, so
      // it gets the same treatment.
      response = null;
    }

    const isColdStart = response === null || COLD_START_STATUS.has(response.status);
    if (isColdStart && attempt < COLD_START_BACKOFF_MS.length) {
      if (!notifiedColdStart) {
        notifiedColdStart = true;
        onColdStart?.(true);
      }
      await sleep(COLD_START_BACKOFF_MS[attempt]);
      continue;
    }

    if (notifiedColdStart) onColdStart?.(false);

    if (response === null) {
      throw new ApiError(0, "network", "Could not reach CareerLayer. Check your connection.", null);
    }
    if (isColdStart) {
      throw new ApiError(
        response.status,
        "server_waking",
        "CareerLayer is still starting up. Give it a moment and try again.",
        response.headers.get("x-request-id"),
      );
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

  createMatch: (resumeId: string, jobDescriptionId: string) =>
    postJson<MatchAccepted>("/v1/matches", {
      resume_id: resumeId,
      job_description_id: jobDescriptionId,
    }),

  listMatches: (params?: { resume_id?: string; job_description_id?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.resume_id) query.set("resume_id", params.resume_id);
    if (params?.job_description_id) query.set("job_description_id", params.job_description_id);
    if (params?.limit) query.set("limit", String(params.limit));
    const qs = query.toString();
    return request<{ items: MatchSummary[]; next_cursor: string | null }>(
      `/v1/matches${qs ? `?${qs}` : ""}`,
    );
  },

  getMatch: (matchRunId: string) => request<MatchRun>(`/v1/matches/${matchRunId}`),

  getMatchGaps: (matchRunId: string) =>
    request<GapAnalysisResponse>(`/v1/matches/${matchRunId}/gaps`),

  matchEventsUrl: (matchRunId: string) => `/v1/matches/${matchRunId}/events`,


  createJob: (payload: {
    raw_text: string;
    title?: string | null;
    company?: string | null;
    location?: string | null;
  }) => postJson<JobAccepted>("/v1/jobs", payload),

  listJobs: () => request<JobSummary[]>("/v1/jobs"),

  getJob: (jobId: string) => request<JobDescription>(`/v1/jobs/${jobId}`),

  getJobRequirements: (jobId: string) => request<JobRequirement[]>(`/v1/jobs/${jobId}/requirements`),

  uploadJob: (
    file: File,
    meta?: { title?: string; company?: string; location?: string },
    onProgress?: (fraction: number) => void,
  ) =>
    new Promise<JobAccepted>((resolve, reject) => {
      const form = new FormData();
      form.append("file", file);
      if (meta?.title) form.append("title", meta.title);
      if (meta?.company) form.append("company", meta.company);
      if (meta?.location) form.append("location", meta.location);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/v1/jobs");
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
          resolve(parsed as JobAccepted);
          return;
        }
        const envelope = (parsed ?? {}) as ErrorEnvelope;
        reject(
          new ApiError(
            xhr.status,
            envelope.error?.code ?? "error",
            envelope.error?.message ?? "The job description upload failed.",
            envelope.request_id ?? null,
          ),
        );
      };
      xhr.onerror = () =>
        reject(new ApiError(0, "network", "The upload could not reach CareerLayer.", null));
      xhr.send(form);
    }),


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
