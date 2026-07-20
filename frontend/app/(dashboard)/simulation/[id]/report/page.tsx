"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { ReportShell } from "@/components/report/ReportShell";
import { SummaryCards } from "@/components/report/SummaryCards";
import { PersonaBreakdown } from "@/components/report/PersonaBreakdown";
import { FailureTimeline } from "@/components/report/FailureTimeline";
import { RiskMatrix } from "@/components/report/RiskMatrix";
import { PivotSuggestions } from "@/components/report/PivotSuggestions";
import { ReportChat } from "@/components/report/ReportChat";
import { ExportActions } from "@/components/report/ExportActions";
import { ViabilitySummaryCard } from "@/components/report/ViabilitySummaryCard";
import { CitationsList } from "@/components/report/CitationsList";
import { PublishIdeaButton } from "@/components/report/PublishIdeaButton";
import { ReportSkeleton, ReportChartSkeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { useReport } from "@/hooks/useReport";

const AdoptionCurveChart = dynamic(
  () => import("@/components/report/AdoptionCurveChart").then((m) => m.AdoptionCurveChart),
  { loading: () => <ReportChartSkeleton />, ssr: false }
);

export default function ReportPage() {
  const params = useParams();
  const simulationId = params.id as string;
  const { report, simulation, loading, error } = useReport(simulationId);

  if (loading) {
    return (
      <div className="max-w-[900px] mx-auto px-6 py-10">
        <ReportSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-[900px] mx-auto px-6 py-10">
        <ErrorState
          title="Report couldn't load"
          message={
            typeof error === "string" ? error : "The simulation report failed to load. This might be a temporary issue."
          }
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="py-20 text-center text-muted-foreground max-w-[900px] mx-auto px-6">
        Report not found.
      </div>
    );
  }

  return (
    <ReportShell simulation={simulation} report={report}>
      <ViabilitySummaryCard report={report} />
      <SummaryCards metrics={report.summary_metrics} />
      <AdoptionCurveChart data={report.adoption_curve} />
      <PersonaBreakdown data={report.persona_breakdown} />
      <FailureTimeline events={report.failure_timeline} />
      <RiskMatrix risks={report.risk_matrix} />
      <PivotSuggestions suggestions={report.pivot_suggestions} insights={report.key_insights} />
      <div className="flex flex-wrap items-center gap-3">
        <ExportActions report={report} />
        <PublishIdeaButton simulationId={simulationId} compact />
      </div>
      <CitationsList citations={report.citations ?? []} />
      <ReportChat simulationId={simulationId} />
    </ReportShell>
  );
}
