"use client";

import type { Report, ViabilitySummary } from "@/lib/types";
import { cn } from "@/lib/utils";

function normalizeViability(report: Report): ViabilitySummary {
  const v = report.viability_summary;
  if (v && typeof v.headline === "string" && typeof v.will_it_work === "string") {
    return {
      verdict_label: typeof v.verdict_label === "string" ? v.verdict_label : "mixed",
      headline: v.headline,
      will_it_work: v.will_it_work,
      what_could_go_wrong: typeof v.what_could_go_wrong === "string" ? v.what_could_go_wrong : "",
      what_would_help: typeof v.what_would_help === "string" ? v.what_would_help : "",
    };
  }
  return deriveViabilityFromMetrics(report);
}

function deriveViabilityFromMetrics(report: Report): ViabilitySummary {
  const m = report.summary_metrics;
  const ar = m.adoption_rate ?? 0;
  const cr = m.churn_rate ?? 0;
  const viral = m.viral_coefficient ?? 0;
  const adopters = m.total_adopters ?? 0;

  if (cr >= 60 && ar < 40) {
    return {
      verdict_label: "struggling",
      headline: "As modeled, this idea would likely struggle to keep customers.",
      will_it_work: `The simulation shows about ${ar.toFixed(0)}% adoption with roughly ${cr.toFixed(0)}% churn (relative to adoption). That usually points to retention or fit issues before you scale.`,
      what_could_go_wrong:
        "People may try the product and leave quickly — pricing, trust, delivery, or the core promise might not match expectations.",
      what_would_help:
        "Focus one segment, tighten onboarding and support, and validate pricing with real customers. Use the risks and pivots below for ideas.",
    };
  }
  if (ar >= 45 && cr <= 40 && viral >= 0.35) {
    return {
      verdict_label: "promising",
      headline: "There are encouraging signals — execution still decides the outcome.",
      will_it_work: `About ${ar.toFixed(0)}% adoption, ${cr.toFixed(0)}% churn, and a viral coefficient around ${viral.toFixed(2)} suggest some people see value. This is a simulation, not proof of product–market fit.`,
      what_could_go_wrong:
        "Scaling too fast, weak operations, or competition could still erode trust and margins.",
      what_would_help:
        "Double down on segments that adopted most and keep unit economics honest as you grow.",
    };
  }
  return {
    verdict_label: "mixed",
    headline: "Results are mixed — refine before you bet big.",
    will_it_work: `Roughly ${ar.toFixed(0)}% adoption and ${cr.toFixed(0)}% churn, with about ${adopters} adopters in the run. The picture is not a clean yes or no.`,
    what_could_go_wrong:
      "You might be winning attention without retention, or succeeding with some groups while others drop off.",
    what_would_help:
      "Run a small real-world test, clarify your primary buyer, and address the biggest risks in the report below.",
  };
}

const verdictStyles: Record<string, { border: string; badge: string; badgeText: string }> = {
  promising: {
    border: "border-emerald-500/35",
    badge: "bg-emerald-500/15",
    badgeText: "text-emerald-300",
  },
  struggling: {
    border: "border-rose-500/35",
    badge: "bg-rose-500/15",
    badgeText: "text-rose-300",
  },
  unclear: {
    border: "border-amber-500/35",
    badge: "bg-amber-500/15",
    badgeText: "text-amber-200",
  },
  mixed: {
    border: "border-amber-500/30",
    badge: "bg-amber-500/12",
    badgeText: "text-amber-200",
  },
};

function verdictBadgeLabel(label: string): string {
  const l = label.toLowerCase();
  if (l === "promising") return "Leaning positive";
  if (l === "struggling") return "High risk";
  if (l === "unclear") return "Incomplete analysis";
  return "Mixed signals";
}

export function ViabilitySummaryCard({ report }: { report: Report }) {
  const v = normalizeViability(report);
  const style = verdictStyles[v.verdict_label.toLowerCase()] ?? verdictStyles.mixed;

  return (
    <section
      className={cn(
        "rounded-2xl border bg-[--bg-surface]/80 p-5 sm:p-6 shadow-lg shadow-black/20",
        style.border
      )}
      aria-labelledby="viability-headline"
    >
      <div className="flex flex-wrap items-center gap-2 gap-y-1 mb-3">
        <h2 id="viability-headline" className="text-lg font-semibold text-[--text-primary] tracking-tight">
          Will it work?
        </h2>
        <span
          className={cn(
            "text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full",
            style.badge,
            style.badgeText
          )}
        >
          {verdictBadgeLabel(v.verdict_label)}
        </span>
      </div>
      <p className="text-base text-white font-medium leading-snug mb-4">{v.headline}</p>
      <div className="space-y-4 text-sm text-[--text-secondary] leading-relaxed">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-300/90 mb-1.5">The straight answer</p>
          <p>{v.will_it_work}</p>
        </div>
        {v.what_could_go_wrong ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-rose-300/85 mb-1.5">What could go wrong</p>
            <p>{v.what_could_go_wrong}</p>
          </div>
        ) : null}
        {v.what_would_help ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-300/85 mb-1.5">What would help</p>
            <p>{v.what_would_help}</p>
          </div>
        ) : null}
      </div>
      <p className="mt-4 text-[11px] text-[--text-tertiary] leading-relaxed border-t border-white/10 pt-3">
        This is a simulation, not a guarantee. Use it with your own judgment and real customer conversations.
      </p>
    </section>
  );
}
