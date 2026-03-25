"use client";

import { PivotSuggestion, KeyInsight } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Lightbulb, ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useWizardStore } from "@/store/wizardStore";

interface Props {
  suggestions: PivotSuggestion[];
  insights: KeyInsight[];
}

const CONFIDENCE_BORDER: Record<PivotSuggestion["confidence"], string> = {
  high: "var(--accent-success)",
  medium: "var(--accent-warning)",
  low: "var(--accent-danger)",
};

const CONFIDENCE_BADGE = {
  low: "text-[#fbbf24] bg-[--accent-warning-muted] border-[rgba(245,158,11,0.25)]",
  medium: "text-[#22d3ee] bg-[rgba(6,182,212,0.10)] border-[rgba(6,182,212,0.25)]",
  high: "text-[#34d399] bg-[--accent-success-muted] border-[rgba(16,185,129,0.25)]",
};

export function PivotSuggestions({ suggestions, insights }: Props) {
  const router = useRouter();
  const setRawIdea = useWizardStore((s) => s.setRawIdea);

  const simulatePivot = (s: PivotSuggestion) => {
    const text = `Simulate pivot: ${s.pivot}. ${s.rationale} Evidence: ${s.evidence_from_simulation}`;
    setRawIdea(text);
    router.push("/new");
  };

  return (
    <div className="space-y-6">
      {suggestions && suggestions.length > 0 && (
        <div className="border border-[--border-subtle] rounded-xl p-6 bg-[--bg-surface]/50">
          <h2 className="text-base font-medium mb-1 text-[--text-primary]">Recommended pivots</h2>
          <p className="text-sm text-muted-foreground mb-4">
            AI-generated strategic adjustments based on simulation results
          </p>
          <div className="space-y-4">
            {suggestions.map((s, i) => (
              <div
                key={i}
                className="relative pl-4 mb-2"
                style={{ borderLeft: `3px solid ${CONFIDENCE_BORDER[s.confidence]}` }}
              >
                <div className="bg-[--bg-surface] border border-[--border-subtle] rounded-[12px] p-5">
                  <div className="flex items-start justify-between mb-2 gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <ArrowRight className="h-4 w-4 text-[--accent-primary] shrink-0" />
                      <span className="text-sm font-medium text-[--text-primary]">{s.pivot}</span>
                    </div>
                    <span
                      className={cn(
                        "text-xs px-2 py-0.5 rounded-full border shrink-0",
                        CONFIDENCE_BADGE[s.confidence]
                      )}
                    >
                      {s.confidence}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground ml-6">{s.rationale}</p>
                  <p className="text-xs text-muted-foreground ml-6 mt-1 italic">
                    Evidence: {s.evidence_from_simulation}
                  </p>
                  <button
                    type="button"
                    onClick={() => simulatePivot(s)}
                    className="mt-3 text-xs text-[--text-accent] hover:text-[--accent-glow] flex items-center gap-1 transition-colors"
                  >
                    Simulate this pivot →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {insights && insights.length > 0 && (
        <div className="border border-[--border-subtle] rounded-xl p-6 bg-[--bg-surface]/50">
          <h2 className="text-base font-medium mb-1 text-[--text-primary]">Key insights</h2>
          <p className="text-sm text-muted-foreground mb-4">Actionable takeaways from the simulation</p>
          <div className="space-y-3">
            {insights.map((insight, i) => (
              <div key={i} className="flex gap-3 border-b border-[--border-subtle] last:border-0 pb-3 last:pb-0">
                <Lightbulb className="h-4 w-4 text-[#fbbf24] mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-[--text-primary]">{insight.insight}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{insight.supporting_evidence}</p>
                  <p className="text-xs text-[--text-accent] mt-1">{insight.actionability}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
