"use client";

import dynamic from "next/dynamic";
import type { Report } from "@/lib/types";
import { Logo } from "@/components/ui/Logo";
import { ReportShell } from "@/components/report/ReportShell";
import { SummaryCards } from "@/components/report/SummaryCards";
import { PersonaBreakdown } from "@/components/report/PersonaBreakdown";
import { FailureTimeline } from "@/components/report/FailureTimeline";
import { RiskMatrix } from "@/components/report/RiskMatrix";
import { PivotSuggestions } from "@/components/report/PivotSuggestions";
import { ReportChartSkeleton } from "@/components/ui/skeleton";

const AdoptionCurveChart = dynamic(
  () => import("@/components/report/AdoptionCurveChart").then((m) => m.AdoptionCurveChart),
  { loading: () => <ReportChartSkeleton />, ssr: false }
);

export function SharedReportView({ report }: { report: Report }) {
  return (
    <div className="min-h-dvh bg-void">
      <header className="border-b border-[--border-subtle] px-6 py-4 flex items-center justify-between gap-4">
        <a href="/" className="inline-flex items-center gap-2" aria-label="Futurus home">
          <Logo />
        </a>
        <span className="text-xs text-[--text-tertiary] font-mono shrink-0">Shared simulation report</span>
      </header>
      <ReportShell simulation={null} report={report} publicShare>
        <SummaryCards metrics={report.summary_metrics} />
        <AdoptionCurveChart data={report.adoption_curve} />
        <PersonaBreakdown data={report.persona_breakdown} />
        <FailureTimeline events={report.failure_timeline} />
        <RiskMatrix risks={report.risk_matrix} />
        <PivotSuggestions suggestions={report.pivot_suggestions} insights={report.key_insights} />
      </ReportShell>
    </div>
  );
}
