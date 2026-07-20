import type {
  FailureEvent,
  KeyInsight,
  PersonaResult,
  PivotSuggestion,
  Report,
  Risk,
  SummaryMetrics,
} from "@/lib/types";

function metricsFromReport(report: Report): SummaryMetrics {
  return report.summary_metrics;
}

function weakStrong(personas: PersonaResult[] | undefined): { weak: string; strong: string } {
  const sorted = [...(personas || [])].sort(
    (a, b) => (a.adoption_rate ?? 0) - (b.adoption_rate ?? 0)
  );
  return {
    weak: sorted[0]?.segment || "some segments",
    strong: sorted[sorted.length - 1]?.segment || "engaged segments",
  };
}

export function heuristicFailureTimeline(report: Report): FailureEvent[] {
  const m = metricsFromReport(report);
  const { weak, strong } = weakStrong(report.persona_breakdown);
  const ar = m.adoption_rate ?? 0;
  const cr = m.churn_rate ?? 0;
  const viral = m.viral_coefficient ?? 0;
  const adopters = m.total_adopters ?? 0;
  return [
    {
      turn: 2,
      month_equivalent: 0.5,
      event: `Early interest appeared, but only about ${ar.toFixed(0)}% of agents adopted by the end of the run.`,
      impact_level: ar < 45 ? "medium" : "low",
      affected_segment: "overall",
    },
    {
      turn: 6,
      month_equivalent: 1.5,
      event: `Churn relative to adopters reached roughly ${cr.toFixed(0)}% — retention friction showed up mid-run.`,
      impact_level: cr >= 40 ? "high" : "medium",
      affected_segment: weak,
    },
    {
      turn: 12,
      month_equivalent: 3.0,
      event: `Referral activity stayed limited (viral coefficient ~${viral.toFixed(2)}); growth leaned on direct adoption.`,
      impact_level: viral < 0.35 ? "medium" : "low",
      affected_segment: strong,
    },
    {
      turn: 18,
      month_equivalent: 4.5,
      event: `By late turns, about ${adopters} adopters remained the core signal — not a clean runaway success.`,
      impact_level: "medium",
      affected_segment: "overall",
    },
  ];
}

export function heuristicRiskMatrix(report: Report): Risk[] {
  const m = metricsFromReport(report);
  const { weak, strong } = weakStrong(report.persona_breakdown);
  const cr = m.churn_rate ?? 0;
  const viral = m.viral_coefficient ?? 0;
  return [
    {
      risk: "Retention drop-off after trial",
      probability: cr >= 40 ? "high" : "medium",
      impact: "high",
      mitigation:
        "Improve onboarding, support, and first-week value so adopters do not churn after trying the product.",
    },
    {
      risk: "Weak word-of-mouth / referral loop",
      probability: viral < 0.35 ? "high" : "low",
      impact: "medium",
      mitigation: "Add a clear invite or share incentive once one segment shows durable usage.",
    },
    {
      risk: `Uneven fit across segments (${weak})`,
      probability: "medium",
      impact: "medium",
      mitigation: `Narrow ICP toward ${strong} before spending on broad acquisition.`,
    },
    {
      risk: "Pricing or willingness-to-pay mismatch",
      probability: "medium",
      impact: "high",
      mitigation: "Run a small paid pilot or pricing interviews before locking the published price.",
    },
    {
      risk: "Optimistic simulation vs real-world friction",
      probability: "medium",
      impact: "medium",
      mitigation: "Treat this report as a stress test — validate the top risks with real customers next.",
    },
  ];
}

export function heuristicPivots(report: Report): PivotSuggestion[] {
  const m = metricsFromReport(report);
  const { strong } = weakStrong(report.persona_breakdown);
  const ar = m.adoption_rate ?? 0;
  const cr = m.churn_rate ?? 0;
  const adopters = m.total_adopters ?? 0;
  return [
    {
      pivot: `Focus GTM on ${strong} first`,
      rationale:
        "Concentrating on the segment that adopted most usually beats a broad launch when results are mixed.",
      confidence: "high",
      evidence_from_simulation: `Overall adoption ~${ar.toFixed(0)}%; strongest modeled segment: ${strong}.`,
    },
    {
      pivot: "Ship a retention-first MVP slice",
      rationale:
        "If churn is elevated, growth channels will burn cash until the core loop retains users.",
      confidence: cr >= 35 ? "high" : "medium",
      evidence_from_simulation: `Churn relative to adopters ~${cr.toFixed(0)}% with ~${adopters} adopters in-run.`,
    },
    {
      pivot: "Test a simpler offer or lower commitment tier",
      rationale:
        "A lighter entry offer can raise trial-to-adopt conversion when hesitation shows up in the sim.",
      confidence: "medium",
      evidence_from_simulation: `Adoption landed near ${ar.toFixed(0)}% — not zero, not runaway.`,
    },
  ];
}

export function heuristicInsights(report: Report): KeyInsight[] {
  const m = metricsFromReport(report);
  const { weak, strong } = weakStrong(report.persona_breakdown);
  const ar = m.adoption_rate ?? 0;
  const cr = m.churn_rate ?? 0;
  const viral = m.viral_coefficient ?? 0;
  const adopters = m.total_adopters ?? 0;
  return [
    {
      insight: `Adoption finished near ${ar.toFixed(0)}% with churn around ${cr.toFixed(0)}% of adopters.`,
      supporting_evidence: `Aggregate simulation metrics; ~${adopters} adopters counted.`,
      actionability:
        "Decide whether retention or acquisition is the first bottleneck before scaling spend.",
    },
    {
      insight: `Referral strength is limited (viral coefficient ~${viral.toFixed(2)}).`,
      supporting_evidence: "Derived from referral vs adoption events in the run.",
      actionability:
        "Do not plan growth that depends on organic virality until one segment refers reliably.",
    },
    {
      insight: `Segment skew: lean into ${strong}; be cautious with ${weak}.`,
      supporting_evidence: "Persona breakdown from the simulation when available.",
      actionability: "Rewrite messaging and onboarding for the stronger segment first.",
    },
  ];
}

/** Prefer stored sections; if empty (LLM miss / old rows), fill from metrics. */
export function withFilledReportSections(report: Report): Report {
  return {
    ...report,
    failure_timeline:
      report.failure_timeline?.length > 0
        ? report.failure_timeline
        : heuristicFailureTimeline(report),
    risk_matrix:
      report.risk_matrix?.length > 0 ? report.risk_matrix : heuristicRiskMatrix(report),
    pivot_suggestions:
      report.pivot_suggestions?.length > 0
        ? report.pivot_suggestions
        : heuristicPivots(report),
    key_insights:
      report.key_insights?.length > 0 ? report.key_insights : heuristicInsights(report),
  };
}
