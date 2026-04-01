"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import * as AlertDialog from "@radix-ui/react-alert-dialog";
import { useReport } from "@/hooks/useReport";
import { ReportShell } from "@/components/report/ReportShell";
import { SummaryCards } from "@/components/report/SummaryCards";
import { PersonaBreakdown } from "@/components/report/PersonaBreakdown";
import { FailureTimeline } from "@/components/report/FailureTimeline";
import { RiskMatrix } from "@/components/report/RiskMatrix";
import { PivotSuggestions } from "@/components/report/PivotSuggestions";
import { ReportChat } from "@/components/report/ReportChat";
import { ExportActions } from "@/components/report/ExportActions";
import { ReportSkeleton, ReportChartSkeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/button";
import type { Report } from "@/lib/types";

const AdoptionCurveChart = dynamic(
  () => import("@/components/report/AdoptionCurveChart").then((m) => m.AdoptionCurveChart),
  { loading: () => <ReportChartSkeleton />, ssr: false }
);

function qualitativeNarrativeFailed(r: Report): boolean {
  const riskBad = r.risk_matrix?.some((x) => x.risk === "Analysis unavailable");
  const insightBad = r.key_insights?.some((x) =>
    (x.insight || "").toLowerCase().includes("encountered an error")
  );
  return Boolean(riskBad || insightBad);
}

export default function ReportPage() {
  const params = useParams();
  const simulationId = params.id as string;
  const { report, simulation, loading, error } = useReport(simulationId);
  const narrativeFailed = useMemo(() => (report ? qualitativeNarrativeFailed(report) : false), [report]);
  const [narrativeDialogOpen, setNarrativeDialogOpen] = useState(false);
  const narrativeDismissed = useRef(false);

  useEffect(() => {
    if (narrativeFailed && !narrativeDismissed.current) {
      setNarrativeDialogOpen(true);
    }
  }, [narrativeFailed]);

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
      <AlertDialog.Root
        open={narrativeDialogOpen}
        onOpenChange={(open) => {
          setNarrativeDialogOpen(open);
          if (!open) narrativeDismissed.current = true;
        }}
      >
        <AlertDialog.Portal>
          <AlertDialog.Overlay className="fixed inset-0 bg-black/60 z-[500] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <AlertDialog.Content className="fixed z-[500] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-[440px] mx-4 bg-[--bg-elevated] border border-[--border-default] rounded-[16px] p-6 shadow-2xl">
            <AlertDialog.Title className="text-base font-semibold text-[--text-primary] mb-2">
              Narrative sections didn&apos;t generate
            </AlertDialog.Title>
            <AlertDialog.Description className="text-sm text-[--text-secondary] leading-relaxed space-y-2">
              <p>
                Charts and segment numbers are still from your simulation. The written risk assessment and key insights
                rely on an extra AI step; that step didn&apos;t complete (often a temporary model or quota issue).
              </p>
              <p>
                Try a <strong className="text-[--text-primary]">new simulation</strong> later, or use{" "}
                <strong className="text-[--text-primary]">Ask the simulation analyst</strong> below to explore results
                in plain language.
              </p>
            </AlertDialog.Description>
            <div className="flex flex-wrap justify-end gap-3 mt-6">
              <AlertDialog.Cancel asChild>
                <Button variant="secondary" size="sm" type="button">
                  OK
                </Button>
              </AlertDialog.Cancel>
              <Button variant="outline" size="sm" type="button" asChild>
                <Link href="/new">New simulation</Link>
              </Button>
            </div>
          </AlertDialog.Content>
        </AlertDialog.Portal>
      </AlertDialog.Root>

      <SummaryCards metrics={report.summary_metrics} />
      <AdoptionCurveChart data={report.adoption_curve} />
      <PersonaBreakdown data={report.persona_breakdown} />
      <FailureTimeline events={report.failure_timeline} />
      <RiskMatrix risks={report.risk_matrix} />
      <PivotSuggestions suggestions={report.pivot_suggestions} insights={report.key_insights} />
      <ExportActions report={report} simulationId={simulationId} />
      <ReportChat simulationId={simulationId} />
    </ReportShell>
  );
}
