"use client";

import { track } from "@vercel/analytics";

const CONSENT_KEY = "futurus-cookie-consent";

export function hasTrackingConsent(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(CONSENT_KEY) === "accepted";
}

export function trackingEnabled(): boolean {
  return process.env.NEXT_PUBLIC_ENABLE_VERCEL_ANALYTICS === "true";
}

export function trackEvent(name: string, properties?: Record<string, string | number | boolean>): void {
  if (!trackingEnabled()) return;
  if (!hasTrackingConsent()) return;
  track(name, properties);
}

export function setTrackingConsent(value: "accepted" | "declined"): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(CONSENT_KEY, value);
}

export function getTrackingConsent(): "accepted" | "declined" | null {
  if (typeof window === "undefined") return null;
  const v = window.localStorage.getItem(CONSENT_KEY);
  if (v === "accepted" || v === "declined") return v;
  return null;
}
