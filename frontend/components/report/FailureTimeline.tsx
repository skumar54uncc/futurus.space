import { FailureEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const IMPACT_COLORS = {
  low: "bg-green-100 text-green-800 border-green-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  critical: "bg-red-100 text-red-800 border-red-200",
};

interface Props {
  events: FailureEvent[];
}

export function FailureTimeline({ events }: Props) {
  if (!events || events.length === 0) return null;

  return (
    <div className="border rounded-xl p-6">
      <h2 className="text-base font-medium mb-1">Critical failure points</h2>
      <p className="text-sm text-muted-foreground mb-4">Key moments where customers dropped off or the model showed stress</p>

      <div className="relative">
        <div className="absolute left-3 top-0 bottom-0 w-px bg-border" />
        <div className="space-y-4">
          {events.map((event, i) => (
            <div key={i} className="flex gap-4 relative">
              <div className={cn("w-6 h-6 rounded-full border-2 flex-shrink-0 z-10", IMPACT_COLORS[event.impact_level])} />
              <div className="flex-1 pb-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium text-muted-foreground">Month {event.month_equivalent}</span>
                  <span className={cn("text-xs px-2 py-0.5 rounded-full border", IMPACT_COLORS[event.impact_level])}>
                    {event.impact_level}
                  </span>
                </div>
                <p className="text-sm">{event.event}</p>
                <p className="text-xs text-muted-foreground mt-1">Affected: {event.affected_segment}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
