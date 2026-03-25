import axios from "axios";

const DEFAULT_BACKEND = "http://localhost:8000";

/**
 * Prefer calling the real API origin from the browser whenever it differs from the page origin.
 * Next.js `rewrites` proxies can omit or mishandle `Authorization`, which makes FastAPI return
 * 403 "Not authenticated" even when the user is signed in with Clerk.
 *
 * Use `/api/backend` only when the app is deliberately configured with the same origin as the API
 * (e.g. single-host deploy behind a gateway).
 */
function resolveBaseURL(): string {
  if (typeof window === "undefined") {
    return process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || DEFAULT_BACKEND;
  }

  const configured = process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || DEFAULT_BACKEND;
  try {
    const apiOrigin = new URL(configured).origin;
    if (apiOrigin !== window.location.origin) {
      return configured.replace(/\/+$/, "");
    }
  } catch {
    return DEFAULT_BACKEND;
  }

  return `${window.location.origin}/api/backend`;
}

async function clerkBearerToken(): Promise<string | null> {
  const read = async () => {
    const session = window.Clerk?.session;
    if (!session) return null;
    try {
      return (await session.getToken()) ?? null;
    } catch {
      return null;
    }
  };

  let token = await read();
  if (token) return token;
  if (window.Clerk && window.Clerk.loaded === false) {
    await new Promise((r) => setTimeout(r, 150));
    token = await read();
  }
  return token;
}

export const api = axios.create({
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(async (config) => {
  config.baseURL = resolveBaseURL();
  if (typeof window !== "undefined") {
    const token = await clerkBearerToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;
    const missingSession =
      status === 401 ||
      (status === 403 && typeof detail === "string" && /not authenticated/i.test(detail));
    if (missingSession && typeof window !== "undefined") {
      const next = window.location.pathname + window.location.search;
      const q = next !== "/" ? `?redirect_url=${encodeURIComponent(next)}` : "";
      window.location.href = `/sign-in${q}`;
    }
    return Promise.reject(error);
  }
);
