"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-dvh flex flex-col items-center justify-center px-6 text-center bg-[--bg-void]">
      <div
        className="w-14 h-14 rounded-full bg-[--accent-danger-muted] flex items-center justify-center mb-5"
        aria-hidden
      >
        <AlertTriangle size={24} className="text-[--accent-danger]" />
      </div>
      <h1 className="text-xl font-medium text-[--text-primary] mb-2">Something went wrong</h1>
      <p className="text-sm text-[--text-secondary] max-w-[320px] mb-8">
        An unexpected error occurred. Try refreshing — if it keeps happening, contact us.
      </p>
      <div className="flex gap-3 flex-wrap justify-center">
        <Button variant="primary" onClick={() => reset()} icon={<RefreshCw size={14} />}>
          Try again
        </Button>
        <Button variant="secondary" onClick={() => (window.location.href = "/")}>
          Go home
        </Button>
      </div>
    </div>
  );
}
