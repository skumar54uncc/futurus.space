import { Risk } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ShieldAlert } from "lucide-react";

const LEVEL_BADGE = {
  low: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  high: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  critical: "bg-red-500/15 text-red-400 border-red-500/30",
};

const LEVEL_LEFT = {
  low: "border-emerald-500/50",
  medium: "border-amber-500/50",
  high: "border-orange-500/60",
  critical: "border-red-500/70",
};

interface Props {
  risks: Risk[];
}

export function RiskMatrix({ risks }: Props) {
  if (!risks || risks.length === 0) return null;

  return (
    <div className="border border-[--border-subtle] rounded-xl p-6 bg-[--bg-surface]/50">
      <h2 className="text-xl font-semibold mb-1 text-[--text-primary]">Risk assessment</h2>
      <p className="text-sm text-[--text-tertiary] mb-6">
        Risks identified from how simulated customers behaved — and how to address each one
      </p>

      <div className="space-y-3">
        {risks.map((risk, i) => {
          const worstLevel = (["critical", "high", "medium", "low"] as const).find(
            (l) => risk.impact === l || risk.probability === l
          ) ?? "medium";
          return (
            <div
              key={i}
              className={cn("border-l-4 bg-[--bg-elevated] border border-[--border-subtle] rounded-xl p-5", LEVEL_LEFT[worstLevel])}
            >
              <div className="flex items-start justify-between gap-3 mb-2 flex-wrap">
                <div className="flex items-center gap-2 min-w-0">
                  <ShieldAlert className="h-4 w-4 text-[--text-tertiary] shrink-0" />
                  <span className="text-sm font-semibold text-white">{risk.risk}</span>
                </div>
                <div className="flex gap-1.5 shrink-0">
                  <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", LEVEL_BADGE[risk.probability] ?? LEVEL_BADGE.medium)}>
                    Probability: {risk.probability}
                  </span>
                  <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", LEVEL_BADGE[risk.impact] ?? LEVEL_BADGE.medium)}>
                    Impact: {risk.impact}
                  </span>
                </div>
              </div>
              <p className="text-sm text-[--text-secondary] leading-relaxed pl-6">
                <span className="text-[--text-tertiary] text-xs uppercase tracking-wide font-semibold block mb-0.5">How to address it</span>
                {risk.mitigation}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
