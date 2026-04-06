"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getTrackingConsent, setTrackingConsent, trackingEnabled } from "@/lib/analytics";

type ConsentState = "accepted" | "declined" | null;

export function CookieConsentBanner() {
  const [consent, setConsent] = useState<ConsentState>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!trackingEnabled()) {
      setReady(true);
      return;
    }
    setConsent(getTrackingConsent());
    setReady(true);
  }, []);

  if (!trackingEnabled()) return null;
  if (!ready || consent !== null) return null;

  return (
    <div className="fixed bottom-4 left-1/2 z-[400] w-[min(96vw,760px)] -translate-x-1/2 rounded-2xl border border-[--border-default] bg-[rgba(3,3,15,0.96)] p-4 shadow-2xl backdrop-blur-xl">
      <p className="text-sm text-[--text-secondary] leading-relaxed">
        We use privacy-friendly analytics to measure page visits and product events only after your consent.
        You can change this choice anytime by clearing site storage.
      </p>
      <p className="mt-2 text-xs text-[--text-tertiary]">
        Read more in our <Link href="/privacy" className="text-indigo-300 hover:text-indigo-200 underline underline-offset-2">Privacy Policy</Link>.
      </p>
      <div className="mt-3 flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => {
            setTrackingConsent("declined");
            setConsent("declined");
          }}
          className="rounded-lg border border-[--border-subtle] px-3 py-2 text-sm text-[--text-secondary] hover:border-[--border-default]"
        >
          Decline
        </button>
        <button
          type="button"
          onClick={() => {
            setTrackingConsent("accepted");
            setConsent("accepted");
          }}
          className="rounded-lg bg-[--accent-primary] px-3 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          Accept analytics
        </button>
      </div>
    </div>
  );
}
