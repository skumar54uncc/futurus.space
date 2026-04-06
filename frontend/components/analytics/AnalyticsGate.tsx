"use client";

import { useEffect, useState } from "react";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";
import { PageTracker } from "@/components/analytics/PageTracker";
import { getTrackingConsent, trackingEnabled } from "@/lib/analytics";

export function AnalyticsGate() {
  const [consent, setConsent] = useState<"accepted" | "declined" | null>(null);

  useEffect(() => {
    setConsent(getTrackingConsent());
  }, []);

  if (!trackingEnabled()) return null;
  if (consent !== "accepted") return null;

  return (
    <>
      <Analytics />
      <SpeedInsights />
      <PageTracker />
    </>
  );
}
