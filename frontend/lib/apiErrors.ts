import { isAxiosError } from "axios";

/** FastAPI may return `detail` as string, object (e.g. daily limit), or validation array */
export type DailyLimitDetail = {
  error: string;
  message: string;
  resets_at?: string;
  plan?: string;
};

function isDailyLimitDetail(d: unknown): d is DailyLimitDetail {
  return (
    typeof d === "object" &&
    d !== null &&
    (d as DailyLimitDetail).error === "daily_limit_reached" &&
    typeof (d as DailyLimitDetail).message === "string"
  );
}

export function parseDailyLimitFromError(err: unknown): DailyLimitDetail | null {
  if (!isAxiosError(err)) return null;
  const d = err.response?.data?.detail;
  return isDailyLimitDetail(d) ? d : null;
}

/** Human-readable reset time in the user's locale (ISO string from API). */
export function formatResetsAt(iso: string | undefined): string | null {
  if (!iso || typeof iso !== "string") return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(t));
  } catch {
    return null;
  }
}

export type LaunchErrorResult =
  | { kind: "daily_limit"; title: string; body: string; resetsAtLabel: string | null }
  | { kind: "toast"; message: string };

/**
 * Classify POST /api/simulations/ errors so the UI can show a modal (quota) or a toast.
 */
export function parseSimulationLaunchError(err: unknown): LaunchErrorResult {
  const lim = parseDailyLimitFromError(err);
  if (lim) {
    const when = formatResetsAt(lim.resets_at);
    const suffix = when ? ` Your credits reset around ${when}.` : "";
    return {
      kind: "daily_limit",
      title: "Daily simulation limit reached",
      body: `${lim.message.trim()}${suffix}`,
      resetsAtLabel: when,
    };
  }

  if (!isAxiosError(err)) {
    return { kind: "toast", message: (err as Error)?.message || "Something went wrong. Please try again." };
  }

  const d = err.response?.data?.detail;
  const status = err.response?.status;

  if (typeof d === "string") {
    if (/not authenticated/i.test(d)) {
      return {
        kind: "toast",
        message: "You’re not signed in or your session expired. Refresh the page or sign in again.",
      };
    }
    return { kind: "toast", message: d };
  }

  if (Array.isArray(d)) {
    const parts = d.map((x: { msg?: string }) => (typeof x?.msg === "string" ? x.msg : JSON.stringify(x)));
    return { kind: "toast", message: parts.join(" ") || "Request could not be completed." };
  }

  if (d != null && typeof d === "object" && "message" in d && typeof (d as { message: string }).message === "string") {
    return { kind: "toast", message: (d as { message: string }).message };
  }

  if (d != null && typeof d === "object") {
    return {
      kind: "toast",
      message: "Something went wrong. Please try again or contact support if this continues.",
    };
  }

  if (status) {
    return {
      kind: "toast",
      message: `Request failed (${status}). Check that the API is reachable and try again.`,
    };
  }

  return { kind: "toast", message: err.message || "Network error." };
}

/** Plain string for toasts when you are not using the modal flow */
export function formatSimulationLaunchError(err: unknown): string {
  const r = parseSimulationLaunchError(err);
  if (r.kind === "daily_limit") return r.body;
  return r.message;
}
