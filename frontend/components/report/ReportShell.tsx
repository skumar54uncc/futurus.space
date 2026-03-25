"use client";
import { Simulation, Report } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

interface Props {
  simulation: Simulation | null;
  report: Report;
  children: React.ReactNode;
  /** Public share link: home + headline from report payload */
  publicShare?: boolean;
}

export function ReportShell({ simulation, report, children, publicShare }: Props) {
  const [showTooltip, setShowTooltip] = useState(false);

  const title =
    simulation?.business_name ||
    report.business_name ||
    "Simulation Report";
  const subtitle = simulation?.idea_description || report.idea_description || "";

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <Link
        href={publicShare ? "/" : "/dashboard"}
        className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors mb-6 -ml-1"
      >
        <ArrowLeft className="h-4 w-4 shrink-0" aria-hidden />
        {publicShare ? "Back to Futurus" : "Back to dashboard"}
      </Link>
      <div className="mb-8">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-serif italic text-white">{title}</h1>
            {subtitle ? <p className="text-sm text-slate-400 mt-1">{subtitle}</p> : null}
            {publicShare ? (
              <p className="text-xs text-slate-600 mt-2 font-mono">Shared read-only report</p>
            ) : null}
          </div>
          <div
            className="relative"
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
          >
            <Badge variant="success" className="cursor-help">
              {report.summary_metrics.confidence_score}% confidence
            </Badge>
            {showTooltip && (
              <div className="absolute right-0 top-full mt-2 w-72 p-3 text-xs text-white bg-gray-900 rounded-lg shadow-lg z-50 leading-relaxed">
                <p className="font-medium mb-1">What does this score mean?</p>
                <p>
                  Computed from <span className="text-gray-200">this run&apos;s data</span>: how similar
                  adoption and churn are across segments, how stable net growth is turn-to-turn, how
                  smooth cumulative adoption is, and how many adoption events we saw vs. agent count.
                  It is <span className="text-gray-200">not</span> a guarantee of real-world accuracy.
                </p>
                <p className="mt-1.5 text-gray-400">
                  Higher = segments and dynamics agree; lower = conflicting segments, spiky turns, or
                  a jagged adoption curve. Scores vary by simulation.
                </p>
                <span className="absolute bottom-full right-4 border-4 border-transparent border-b-gray-900" />
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="space-y-6">{children}</div>
    </div>
  );
}
