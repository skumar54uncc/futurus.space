import { Risk } from "@/lib/types";
import { cn } from "@/lib/utils";

const LEVEL_COLORS = {
  low: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-red-100 text-red-700",
};

interface Props {
  risks: Risk[];
}

export function RiskMatrix({ risks }: Props) {
  if (!risks || risks.length === 0) return null;

  return (
    <div className="border rounded-xl p-6">
      <h2 className="text-base font-medium mb-1">Risk assessment</h2>
      <p className="text-sm text-muted-foreground mb-4">Identified risks from simulation behavior patterns</p>

      <div className="space-y-3">
        {risks.map((risk, i) => (
          <div key={i} className="border rounded-lg p-4">
            <div className="flex items-start justify-between mb-2">
              <span className="text-sm font-medium">{risk.risk}</span>
              <div className="flex gap-1.5">
                <span className={cn("text-xs px-2 py-0.5 rounded-full", LEVEL_COLORS[risk.probability])}>
                  P: {risk.probability}
                </span>
                <span className={cn("text-xs px-2 py-0.5 rounded-full", LEVEL_COLORS[risk.impact])}>
                  I: {risk.impact}
                </span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">{risk.mitigation}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
