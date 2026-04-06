"use client";

import { useState, useEffect } from "react";
import { Rocket, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import toast from "react-hot-toast";

interface Props {
  simulationId: string;
}

export function PublishIdeaButton({ simulationId }: Props) {
  const [published, setPublished] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .get<{ published: boolean }>(`/api/ideas/${simulationId}/status`)
      .then(({ data }) => {
        if (!cancelled) setPublished(data.published);
      })
      .catch(() => {
        if (!cancelled) setPublished(false);
      });
    return () => {
      cancelled = true;
    };
  }, [simulationId]);

  const handlePublish = async () => {
    setLoading(true);
    try {
      await api.post(`/api/ideas/${simulationId}/publish`);
      setPublished(true);
      toast.success("Idea published to the public dashboard!");
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (detail === "This idea is already published") {
        setPublished(true);
        toast.success("Already published!");
      } else {
        toast.error(detail || "Failed to publish idea. Try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUnpublish = async () => {
    setLoading(true);
    try {
      await api.delete(`/api/ideas/${simulationId}/unpublish`);
      setPublished(false);
      toast.success("Idea removed from the public dashboard.");
    } catch {
      toast.error("Failed to unpublish. Try again.");
    } finally {
      setLoading(false);
    }
  };

  // Still checking status
  if (published === null) return null;

  if (published) {
    return (
      <div className="flex items-center gap-3 mt-6 p-4 rounded-[14px] border border-emerald-500/20 bg-emerald-500/5">
        <Check size={18} className="text-emerald-400 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-emerald-400">Published to Ideas Dashboard</p>
          <p className="text-xs text-[--text-tertiary] mt-0.5">
            Your idea is visible on the public ideas page.
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleUnpublish}
          loading={loading}
          className="text-[--text-tertiary] hover:text-red-400 shrink-0"
        >
          Unpublish
        </Button>
      </div>
    );
  }

  return (
    <div className="mt-6">
      <Button
        onClick={handlePublish}
        loading={loading}
        variant="primary"
        size="lg"
        className="w-full sm:w-auto"
      >
        <Rocket size={16} />
        Publish the Idea
      </Button>
      <p className="text-xs text-[--text-tertiary] mt-2">
        We will email you when the report is ready.
      </p>
    </div>
  );
}
