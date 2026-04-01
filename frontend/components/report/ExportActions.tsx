"use client";
import { useState } from "react";
import { Report } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Share2 } from "lucide-react";
import toast from "react-hot-toast";

interface Props {
  report: Report;
}

export function ExportActions({ report }: Props) {
  const [copied, setCopied] = useState(false);

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
      <Button variant="outline" onClick={handleShare}>
        <Share2 className="h-4 w-4 mr-2" />
        {copied ? "Copied!" : "Share link"}
      </Button>
    </div>
  );
}
