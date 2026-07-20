import type { Report, ViabilitySummary } from "./types";

/** Legacy error payload from older backends before heuristic fallback. */
export function hasLegacyNarrativeErrorMarkers(report: Report): boolean {
  const riskBad = report.risk_matrix?.some((x) => x.risk === "Analysis unavailable");
  const insightBad = report.key_insights?.some((x) =>
    (x.insight || "").toLowerCase().includes("encountered an error")
  );
  return Boolean(riskBad || insightBad);
}

export function isHeuristicNarrative(report: Report): boolean {
  const src = report.viability_summary?.narrative_source;
  return src === "heuristic";
}

/** Quiet banner only — never a blocking modal. */
export function shouldShowNarrativeGapNote(report: Report): boolean {
  return isHeuristicNarrative(report) || hasLegacyNarrativeErrorMarkers(report);
}

export function looksLikePoisonedUnclearVerdict(v: Pick<ViabilitySummary, "verdict_label" | "headline" | "will_it_work">): boolean {
  if ((v.verdict_label || "").toLowerCase() !== "unclear") return false;
  const blob = `${v.headline || ""} ${v.will_it_work || ""}`.toLowerCase();
  return (
    blob.includes("could not finish") ||
    blob.includes("analysis unavailable") ||
    blob.includes("ai step that writes") ||
    blob.includes("did not complete")
  );
}

export function formatVerdictBadgeLabel(
  label: string,
  split: { yes: number; no: number }
): string {
  const l = label.toLowerCase();
  if (l === "promising") return `Leaning yes (${split.yes}% / ${split.no}%)`;
  if (l === "struggling") return `Leaning no (${split.yes}% / ${split.no}%)`;
  // "unclear" used to mean LLM failure — treat as mixed metrics, not incomplete.
  return `Yes ${split.yes}% / No ${split.no}%`;
}
