"use client";

import { useEffect, useRef } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { trackEvent } from "@/lib/analytics";

export function PageTracker() {
  const pathname = usePathname();
  const search = useSearchParams();
  const prev = useRef<string>("");

  useEffect(() => {
    const qs = search?.toString();
    const url = qs ? `${pathname}?${qs}` : pathname;
    if (!url || prev.current === url) return;
    prev.current = url;
    trackEvent("page_view", { path: pathname || "/" });
  }, [pathname, search]);

  return null;
}
