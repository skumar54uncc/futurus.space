/**
 * Lightweight asserts for reportNarrative helpers (no frontend test runner).
 * Run: node --experimental-strip-types lib/reportNarrative.selftest.ts
 * from frontend/ (Node 22+) or via npx tsx.
 */
import {
  formatVerdictBadgeLabel,
  hasLegacyNarrativeErrorMarkers,
  isHeuristicNarrative,
  looksLikePoisonedUnclearVerdict,
  shouldShowNarrativeGapNote,
} from "./reportNarrative";

function assert(cond: unknown, msg: string) {
  if (!cond) throw new Error(msg);
}

const split = { yes: 58, no: 42 };

assert(
  formatVerdictBadgeLabel("unclear", split) === "Yes 58% / No 42%",
  "unclear must not say Incomplete analysis"
);
assert(
  formatVerdictBadgeLabel("promising", split).includes("Leaning yes"),
  "promising badge"
);
assert(
  looksLikePoisonedUnclearVerdict({
    verdict_label: "unclear",
    headline: "We could not finish the written analysis for this run.",
    will_it_work: "The AI step that writes the narrative did not complete",
  }),
  "detect poisoned unclear"
);
assert(
  !looksLikePoisonedUnclearVerdict({
    verdict_label: "mixed",
    headline: "Results are mixed",
    will_it_work: "Roughly 40% adoption",
  }),
  "healthy mixed is fine"
);

const heuristicReport = {
  risk_matrix: [],
  key_insights: [],
  viability_summary: { narrative_source: "heuristic" },
} as any;

assert(isHeuristicNarrative(heuristicReport), "heuristic source");
assert(shouldShowNarrativeGapNote(heuristicReport), "quiet note for heuristic");
assert(!hasLegacyNarrativeErrorMarkers(heuristicReport), "no legacy markers");

const legacy = {
  risk_matrix: [{ risk: "Analysis unavailable" }],
  key_insights: [{ insight: "Report generation encountered an error" }],
  viability_summary: { narrative_source: "llm" },
} as any;

assert(hasLegacyNarrativeErrorMarkers(legacy), "legacy markers");
assert(shouldShowNarrativeGapNote(legacy), "quiet note for legacy");

console.log("reportNarrative.selftest: ok");
