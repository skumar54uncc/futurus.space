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
    <div ref={ref} className="mb-5">
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-[--text-primary] font-medium capitalize">{label}</span>
        <span className="text-[--text-tertiary] font-mono">{row.adoption_rate.toFixed(1)}% adopted</span>
      </div>
      <div className="h-2 rounded-full bg-[--bg-elevated] overflow-hidden mb-1">
        <div
          className="h-full rounded-full bg-[--accent-primary] transition-all duration-700 ease-out"
          style={{ width: inView ? `${Math.min(100, row.adoption_rate)}%` : "0%" }}
        />
      </div>
      <div className="h-1.5 rounded-full bg-[--bg-elevated] overflow-hidden">
        <div
          className="h-full rounded-full bg-[#f87171] transition-all duration-700 ease-out"
          style={{
            width: inView ? `${Math.min(100, row.churn_rate)}%` : "0%",
            transitionDelay: "100ms",
          }}
        />
      </div>
      <div className="flex justify-between text-xs text-[--text-tertiary] mt-1">
        <span>{row.churn_rate.toFixed(1)}% churned</span>
        <span className="font-mono">{row.referrals_generated} referrals</span>
      </div>
    </div>
  );
}

export function PersonaBreakdown({ data }: Props) {
  return (
    <div className="border border-[--border-subtle] rounded-xl p-6 bg-[--bg-surface]/50">
      <h2 className="text-base font-medium mb-1 text-[--text-primary]">Customer segment analysis</h2>
      <p className="text-sm text-muted-foreground mb-6">How each customer archetype interacted with your product</p>
      <div>
        {data.map((row) => (
          <SegmentBar key={row.segment} row={row} />
        ))}
      </div>
    </div>
  );
}
