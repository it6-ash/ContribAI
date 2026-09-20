import type {
  Health,
  Level,
  Issue,
  Plan,
  Profile,
  Recommendation,
  RecommendationsResponse,
  RefreshStatus,
  Repository,
  Taxonomy,
  User,
} from "./types";

// Empty means same-origin: requests go to /api/* and next.config.ts rewrites them
// to the backend. Keeping the browser on one origin is what makes the session
// cookie work at all once the API is not on localhost. Override only if you
// deliberately want the browser talking to another host, and read the
// SameSite note in next.config.ts before you do.
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly retryAfterSeconds?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api${path}`, {
      credentials: "include", // session cookie is httpOnly; the token never reaches JS
      headers: init.body ? { "Content-Type": "application/json" } : undefined,
      cache: "no-store",
      ...init,
    });
  } catch {
    throw new ApiError(
      `Cannot reach the ContribAI API at ${API_BASE}. Is the backend running?`,
      0,
    );
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body.detail ?? `Request failed (${res.status})`,
      res.status,
      body.retry_after_seconds,
    );
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const api = {
  health: () => request<Health>("/health"),
  taxonomy: () => request<Taxonomy>("/taxonomy"),

  me: () => request<User>("/me"),
  loginDemo: (username: string) =>
    request<{ user: User }>(`/auth/demo?username=${encodeURIComponent(username)}`, {
      method: "POST",
    }),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  githubLoginUrl: () => `${API_BASE}/api/auth/github`,

  profile: () => request<Profile>("/profile"),
  analyzeProfile: () => request<Profile>("/profile/analyze", { method: "POST" }),
  updateProfile: (payload: {
    experience_level?: string;
    mode?: string;
    interests?: string[];
    // Objects carry the user's claimed level; bare strings still work and
    // default to intermediate server-side.
    skills?: Array<{ name: string; level: Level } | string>;
  }) => request<Profile>("/profile", { method: "PUT", body: JSON.stringify(payload) }),

  recommendations: (limit = 6, refresh = false) =>
    request<RecommendationsResponse>(
      `/recommendations?limit=${limit}&refresh=${refresh}`,
    ),
  recommendation: (id: number) => request<Recommendation>(`/recommendations/${id}`),

  refreshStatus: () => request<RefreshStatus>("/refresh/status"),
  refreshCorpus: () =>
    request<{ started: boolean; reason?: string; queries: string[] }>(
      "/refresh/corpus",
      { method: "POST" },
    ),

  issue: (id: number) => request<Issue>(`/issues/${id}`),
  explainIssue: (id: number) => request<Issue>(`/issues/${id}/analyze`, { method: "POST" }),

  repository: (id: number) => request<Repository>(`/repositories/${id}`),

  plan: (issueId: number, regenerate = false) =>
    request<Plan>(`/contribution/${issueId}/plan?regenerate=${regenerate}`, {
      method: "POST",
    }),
  chat: (issueId: number, question: string) =>
    request<{ answer: string; source: string }>(`/contribution/${issueId}/chat`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
};

export function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function hoursLabel(min: number, max: number): string {
  const fmt = (n: number) => (Number.isInteger(n) ? n : n.toFixed(1));
  return `${fmt(min)}-${fmt(max)}h`;
}
