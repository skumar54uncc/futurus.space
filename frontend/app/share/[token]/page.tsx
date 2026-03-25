import { notFound } from "next/navigation";
import type { Report } from "@/lib/types";
import { SharedReportView } from "@/components/report/SharedReportView";

async function fetchSharedReport(token: string): Promise<Report | null> {
  const base = (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
  try {
    const res = await fetch(`${base}/api/reports/share/${encodeURIComponent(token)}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as Report;
  } catch {
    return null;
  }
}

export default async function SharedReportPage({ params }: { params: { token: string } }) {
  const report = await fetchSharedReport(params.token);
  if (!report) notFound();

  return (
    <main id="main-content" className="relative z-[1]">
      <SharedReportView report={report} />
    </main>
  );
}
