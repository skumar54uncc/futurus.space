/**
 * Run: npx --yes tsx lib/reportSectionFallbacks.selftest.ts
 */
import { withFilledReportSections } from "./reportSectionFallbacks";
import type { Report } from "./types";

function assert(cond: unknown, msg: string) {
  if (!cond) throw new Error(msg);
}

const emptyReport = {
  id: "1",
  simulation_id: "2",
  summary_metrics: {
    adoption_rate: 42,
    churn_rate: 55,
    viral_coefficient: 0.2,
    total_adopters: 30,
    total_churned: 16,
    confidence_score: 50,
  },
  adoption_curve: [],
  persona_breakdown: [
    { segment: "students", adoption_rate: 20, churn_rate: 60, referrals_generated: 0 },
    { segment: "pros", adoption_rate: 70, churn_rate: 20, referrals_generated: 5 },
  ],
  failure_timeline: [],
  risk_matrix: [],
  pivot_suggestions: [],
  key_insights: [],
  created_at: new Date().toISOString(),
} as Report;

const filled = withFilledReportSections(emptyReport);
assert(filled.failure_timeline.length >= 3, "timeline filled");
assert(filled.risk_matrix.length >= 3, "risks filled");
assert(filled.pivot_suggestions.length >= 2, "pivots filled");
assert(filled.key_insights.length >= 2, "insights filled");
assert(
  filled.risk_matrix.some((r) => r.risk.includes("Retention")),
  "retention risk present"
);

const kept = withFilledReportSections({
  ...emptyReport,
  risk_matrix: [
    {
      risk: "Keep me",
      probability: "low",
      impact: "low",
      mitigation: "n/a",
    },
  ],
});
assert(kept.risk_matrix.length === 1 && kept.risk_matrix[0].risk === "Keep me", "keep stored");

console.log("reportSectionFallbacks.selftest: ok");
