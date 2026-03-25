const STATUS_LABEL: Record<string, string> = {
  queued: "Queued…",
  building_seed: "Building market seed…",
  generating_personas: "Creating personas…",
  running: "Simulation running…",
  generating_report: "Generating report…",
  completed: "Simulation complete",
  failed: "Simulation failed",
};

interface SimulationProgressBarProps {
  progress: number;
  status: string;
}

export function SimulationProgressBar({ progress, status }: SimulationProgressBarProps) {
  const pct = Math.min(100, Math.max(0, progress));
  const indeterminate = status === "queued";

  return (
    <div className="w-full max-w-xl mx-auto space-y-3">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-mono font-semibold tabular-nums text-[--text-primary] min-w-[2.75rem]">
          {indeterminate ? "—" : `${Math.round(pct)}%`}
        </span>
        <span className="text-[--text-secondary] text-right text-xs sm:text-sm serif italic">
          {STATUS_LABEL[status] ?? status}
        </span>
      </div>
      <div
        className="h-3 w-full rounded-full bg-[--bg-elevated] border border-[--border-subtle] overflow-hidden relative"
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-busy={indeterminate}
        aria-label="Simulation progress"
      >
        {indeterminate ? (
          <div
            className="absolute inset-y-0 left-0 w-[38%] rounded-full bg-[--accent-primary] shadow-[0_0_16px_rgba(99,102,241,0.45)] motion-safe:animate-nav-indeterminate"
            style={{ willChange: "transform" }}
          />
        ) : (
          <div
            className={`h-full rounded-full transition-[width] duration-500 ease-out ${
              pct >= 100 ? "bg-[--accent-success]" : "bg-[--accent-primary]"
            }`}
            style={{
              width: `${pct}%`,
              boxShadow: pct > 0 && pct < 100 ? "0 0 20px rgba(99, 102, 241, 0.35)" : undefined,
            }}
          />
        )}
      </div>
    </div>
  );
}
