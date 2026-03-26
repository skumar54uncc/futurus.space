import { FailureEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const IMPACT_STYLES = {
  low: {
    dot: "bg-emerald-500/20 border-emerald-500/50",
    badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    line: "bg-emerald-500/40",
  },
  medium: {
    dot: "bg-amber-500/20 border-amber-500/50",
    badge: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    line: "bg-amber-500/40",
  },
  high: {
    dot: "bg-orange-500/20 border-orange-500/50",
    badge: "bg-orange-500/15 text-orange-400 border-orange-500/30",
    line: "bg-orange-500/40",
  },
  critical: {
    dot: "bg-red-500/20 border-red-500/60",
    badge: "bg-red-500/15 text-red-400 border-red-500/30",
    line: "bg-red-500/50",
  },
};

const IMPACT_LABELS = {
  low: "Low impact",
  medium: "Medium impact",
  high: "High impact",
  critical: "Critical",
};

interface Props {
  events: FailureEvent[];
}

export function FailureTimeline({ events }: Props) {
  if (!events || events.length === 0) return null;

  return (
    <div className="border border-[--border-subtle] rounded-xl p-6 bg-[--bg-surface]/50">
      <h2 className="text-xl font-semibold mb-1 text-[--text-primary]">Critical failure points</h2>
      <p className="text-sm text-[--text-tertiary] mb-6">
        Key moments where customers dropped off or showed resistance
      </p>

      <div className="relative">
        <div className="absolute left-[11px] top-2 bottom-2 w-px bg-[--border-subtle]" />
        <div className="space-y-5">
          {events.map((event, i) => {
            const s = IMPACT_STYLES[event.impact_level] ?? IMPACT_STYLES.medium;
            return (
              <div key={i} className="flex gap-4 relative">
                <div className={cn("w-6 h-6 rounded-full border-2 flex-shrink-0 z-10 mt-0.5", s.dot)} />
                <div className="flex-1 bg-[--bg-elevated] border border-[--border-subtle] rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <span className="text-xs font-semibold text-[--text-secondary] bg-[--bg-surface] border border-[--border-subtle] px-2 py-0.5 rounded-full">
                      Month {event.month_equivalent}
                    </span>
                    <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", s.badge)}>
                      {IMPACT_LABELS[event.impact_level] ?? event.impact_level}
                    </span>
                  </div>
                  <p className="text-sm text-white font-medium leading-snug">{event.event}</p>
                  <p className="text-xs text-[--text-tertiary] mt-1.5">
                    Affected segment: <span className="text-[--text-secondary]">{event.affected_segment}</span>
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
