"use client";

import { PersonaResult } from "@/lib/types";
import { useInView } from "@/hooks/useInView";

interface Props {
  data: PersonaResult[];
}

function SegmentBar({ row }: { row: PersonaResult }) {
  const { ref, inView } = useInView();
  const label = row.segment.replace(/_/g, " ");

  return (
    <div ref={ref} className="mb-6 pb-6 border-b border-[--border-subtle] last:border-0 last:mb-0 last:pb-0">
      <div className="flex justify-between items-center mb-2 gap-2">
        <span className="text-sm text-white font-medium capitalize leading-snug">{label}</span>
        <span className="text-sm font-bold text-[#34d399] shrink-0 tabular-nums">
          {row.adoption_rate.toFixed(1)}% adopted
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-[--bg-elevated] overflow-hidden mb-1.5">
        <div
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-[#34d399] transition-all duration-700 ease-out"
          style={{ width: inView ? `${Math.min(100, row.adoption_rate)}%` : "0%" }}
        />
      </div>
      <div className="h-1.5 rounded-full bg-[--bg-elevated] overflow-hidden mb-2">
        <div
          className="h-full rounded-full bg-[#f87171] transition-all duration-700 ease-out"
          style={{ width: inView ? `${Math.min(100, row.churn_rate)}%` : "0%", transitionDelay: "100ms" }}
        />
      </div>
      <div className="flex justify-between text-xs mt-1">
        <span className="text-[#f87171] font-medium">
          {row.churn_rate.toFixed(1)}% of adopters churned
        </span>
        <span className="text-[#818cf8] font-medium tabular-nums">{row.referrals_generated} referrals</span>
      </div>
    </div>
  );
}

export function PersonaBreakdown({ data }: Props) {
  return (
    <div className="border border-[--border-subtle] rounded-xl p-6 bg-[--bg-surface]/50">
      <h2 className="text-xl font-semibold mb-1 text-[--text-primary]">Customer segment analysis</h2>
      <p className="text-sm text-[--text-tertiary] mb-2">
        How each type of customer interacted with your product
      </p>
      <p className="text-xs text-[--text-tertiary]/90 mb-6 leading-relaxed">
        <span className="text-[--text-secondary]">Adopted</span> = share of agents in that segment who adopted.
        <span className="mx-1 text-[--border-subtle]">·</span>
        <span className="text-[--text-secondary]">Churn</span> = share of those adopters who later churned (not the whole
        segment), so both bars can look high without being contradictory.
      </p>
      <div>
        {data.map((row) => (
          <SegmentBar key={row.segment} row={row} />
        ))}
      </div>
    </div>
  );
}
