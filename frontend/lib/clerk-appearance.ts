import { dark } from "@clerk/themes";

/**
 * Public base URL for this frontend (no trailing slash). Used so Clerk can load the logo via absolute URL.
 * On Vercel, VERCEL_URL is set automatically; override with NEXT_PUBLIC_SITE_URL for production domain.
 */
export function getClerkLogoAbsoluteUrl(): string {
  const trimmed = process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/+$/, "");
  if (trimmed) {
    return `${trimmed}/brand/futurus-logo-dark.svg`;
  }
  if (process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL}/brand/futurus-logo-dark.svg`;
  }
  if (process.env.NODE_ENV === "development") {
    return "http://localhost:3000/brand/futurus-logo-dark.svg";
  }
  return "https://futurus.dev/brand/futurus-logo-dark.svg";
}

/** Matches Futurus globals.css (--accent-primary, dark surfaces). */
export const futurusClerkTheme = {
  baseTheme: dark,
  variables: {
    colorPrimary: "#6366f1",
    colorPrimaryForeground: "#ffffff",
    colorBackground: "#05050f",
    colorInputBackground: "#101028",
    colorText: "#f1f5f9",
    colorTextSecondary: "#94a3b8",
    colorTextOnPrimaryBackground: "#ffffff",
    colorNeutral: "#475569",
    borderRadius: "10px",
  },
} as const;

/** Call from server components so VERCEL_URL / env resolve per deploy. */
export function getFuturusClerkAppearance() {
  return {
    ...futurusClerkTheme,
    layout: {
      logoImageUrl: getClerkLogoAbsoluteUrl(),
    },
  } as const;
}

/** For client-only Clerk widgets (e.g. UserProfile): prefers NEXT_PUBLIC_SITE_URL, else current origin. */
export function getClerkLogoUrlForClient(): string | undefined {
  const base = process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/+$/, "");
  if (base) {
    return `${base}/brand/futurus-logo-dark.svg`;
  }
  if (typeof window !== "undefined") {
    return `${window.location.origin}/brand/futurus-logo-dark.svg`;
  }
  return undefined;
}
