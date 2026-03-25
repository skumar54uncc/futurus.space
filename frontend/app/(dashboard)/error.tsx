"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw, LayoutDashboard } from "lucide-react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center">
      <div
        className="w-12 h-12 rounded-full bg-[--accent-danger-muted] flex items-center justify-center mb-4"
        aria-hidden
      >
        <AlertTriangle size={20} className="text-[--accent-danger]" />
      </div>
      <h2 className="text-base font-medium text-[--text-primary] mb-2">Page failed to load</h2>
      <p className="text-sm text-[--text-secondary] max-w-[280px] mb-6">
        Something went wrong loading this section. Try again or go back to the dashboard.
      </p>
      <div className="flex gap-3 flex-wrap justify-center">
        <Button variant="primary" size="sm" onClick={() => reset()} icon={<RefreshCw size={13} />}>
          Retry
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => router.push("/dashboard")}
          icon={<LayoutDashboard size={13} />}
        >
          Dashboard
        </Button>
      </div>
    </div>
  );
}
