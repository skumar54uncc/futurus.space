"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Report } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Download, Share2 } from "lucide-react";
import toast from "react-hot-toast";

interface Props {
  report: Report;
  simulationId: string;
}

export function ExportActions({ report, simulationId }: Props) {
  const [exporting, setExporting] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleExportPDF = async () => {
    setExporting(true);
    const sid = encodeURIComponent(String(simulationId).trim());
    try {
      const { data } = await api.get<{ pdf_url: string; format?: "pdf" | "html" }>(
        `/api/reports/${sid}/export/pdf`
      );

      if (!data?.pdf_url) {
        toast.error("No download URL returned. Please try again.");
        return;
      }

      const isPresigned =
        data.pdf_url.includes("X-Amz-Signature") ||
        data.pdf_url.includes("x-amz-signature") ||
        !data.pdf_url.includes("amazonaws.com");

      if (!isPresigned && data.pdf_url.includes("amazonaws.com")) {
        toast.error("Could not sign the download URL — check AWS credentials on the server.");
        return;
      }

      const backendUrl = (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
      const fullUrl = data.pdf_url.startsWith("http") ? data.pdf_url : `${backendUrl}${data.pdf_url}`;

      if (data.format === "html") {
        toast.success(
          "Report opened as HTML (PDF generation unavailable on this server). Use Print → Save as PDF if you need a file.",
          { duration: 6000 }
        );
      } else {
        toast.success("PDF ready — opening in new tab.");
      }
      window.open(fullUrl, "_blank", "noopener,noreferrer");
    } catch (err: unknown) {
      console.error("Export failed:", err);
      const ax = err as { response?: { data?: { detail?: unknown }; status?: number } };
      const d = ax.response?.data?.detail;
      const msg =
        typeof d === "string"
          ? d
          : ax.response?.status === 403
            ? "You don’t have access to export this report."
            : ax.response?.status === 404
              ? "Report not found."
              : "Failed to generate export — check that the API is running and try again.";
      toast.error(msg);
    } finally {
      setExporting(false);
    }
  };

  const handleShare = () => {
    if (report.share_token) {
      const url = `${window.location.origin}/share/${report.share_token}`;
      navigator.clipboard.writeText(url);
      setCopied(true);
      toast.success("Share link copied!");
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="flex items-center gap-3">
      <Button variant="outline" onClick={() => void handleExportPDF()} loading={exporting}>
        <Download className="h-4 w-4 mr-2" />
        Export report
      </Button>
      <Button variant="outline" onClick={handleShare}>
        <Share2 className="h-4 w-4 mr-2" />
        {copied ? "Copied!" : "Share link"}
      </Button>
    </div>
  );
}
