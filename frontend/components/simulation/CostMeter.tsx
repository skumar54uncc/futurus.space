"use client";
import { formatCurrency } from "@/lib/utils";

interface Props {
  currentCost: number;
  maxCost: number;
}

export function CostMeter({ currentCost, maxCost }: Props) {
  const percentage = Math.min(100, (currentCost / maxCost) * 100);

  return (
    <div className="bg-muted rounded-lg p-4">
      <div className="flex justify-between text-xs text-muted-foreground mb-1">
        <span>LLM cost</span>
        <span>{formatCurrency(currentCost)} / {formatCurrency(maxCost)}</span>
      </div>
      <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
