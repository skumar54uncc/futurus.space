"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  TrendingUp,
  Shield,
  Share2,
  Wrench,
  Star,
  ChevronDown,
  Lightbulb,
  ArrowUpDown,
  ArrowLeft,
  RefreshCw,
  Plus,
} from "lucide-react";
import { api } from "@/lib/api";
import type { PublishedIdea, PublishedIdeaList } from "@/lib/types";
import { ErrorState } from "@/components/ui/ErrorState";
import { Navbar } from "@/components/layout/Navbar";

const CATEGORIES = [
  { value: "", label: "All Categories" },
  { value: "SaaS", label: "SaaS" },
  { value: "Consumer App", label: "Consumer App" },
  { value: "Marketplace", label: "Marketplace" },
  { value: "Physical Product", label: "Physical Product" },
  { value: "Service Business", label: "Service Business" },
  { value: "Enterprise", label: "Enterprise" },
];

function ratingColor(score: number): string {
  if (score >= 70) return "text-emerald-400";
  if (score >= 45) return "text-amber-400";
  return "text-red-400";
}

function ratingBg(score: number): string {
  if (score >= 70) return "bg-emerald-500/10 border-emerald-500/20";
  if (score >= 45) return "bg-amber-500/10 border-amber-500/20";
  return "bg-red-500/10 border-red-500/20";
}

function ScorePill({ label, score, icon: Icon }: { label: string; score: number; icon: React.ElementType }) {
  return (
    <div className="flex items-center gap-1.5" title={`${label}: ${score}/100`}>
      <Icon size={12} className="text-[--text-tertiary]" />
      <span className={`text-xs font-medium tabular-nums ${ratingColor(score)}`}>
        {score}
      </span>
    </div>
  );
}

function buildSimulateIdeaPrefill(idea: PublishedIdea): string {
  const merged = `${idea.title}: ${idea.description}`.trim();
  return merged.length > 500 ? `${merged.slice(0, 500)}...` : merged;
}

function IdeaRow({ idea }: { idea: PublishedIdea }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-[--border-subtle] rounded-[14px] bg-[--bg-surface] hover:border-[--border-default] transition-all duration-200">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 sm:p-5 flex items-start gap-4 cursor-pointer"
      >
        <div className="shrink-0 mt-0.5">
          {idea.user_avatar_url ? (
            <img
              src={idea.user_avatar_url}
              alt={idea.user_name}
              className="w-9 h-9 rounded-full object-cover border border-[--border-subtle]"
            />
          ) : (
            <div className="w-9 h-9 rounded-full bg-indigo-500/20 flex items-center justify-center text-xs font-medium text-indigo-400">
              {idea.user_name.charAt(0).toUpperCase()}
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h3 className="text-sm font-medium text-[--text-primary] truncate max-w-[300px]">
              {idea.title}
            </h3>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shrink-0">
              {idea.category}
            </span>
          </div>
          <p className="text-xs text-[--text-tertiary] mb-2">
            by {idea.user_name} &middot;{" "}
            {new Date(idea.created_at).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
              year: "numeric",
            })}
          </p>
          {!expanded && (
            <p className="text-xs text-[--text-secondary] line-clamp-2">
              {idea.description}
            </p>
          )}

          <div className="flex items-center gap-4 mt-3 flex-wrap">
            <ScorePill label="Market Demand" score={idea.score_market_demand} icon={TrendingUp} />
            <ScorePill label="Retention" score={idea.score_retention} icon={Shield} />
            <ScorePill label="Virality" score={idea.score_virality} icon={Share2} />
            <ScorePill label="Feasibility" score={idea.score_feasibility} icon={Wrench} />
          </div>
        </div>

        <div className="shrink-0 flex flex-col items-center gap-1">
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[10px] border ${ratingBg(idea.overall_rating)}`}
          >
            <Star size={14} className={ratingColor(idea.overall_rating)} />
            <span className={`text-base font-semibold tabular-nums ${ratingColor(idea.overall_rating)}`}>
              {idea.overall_rating}
            </span>
          </div>
          <span className="text-[10px] text-[--text-tertiary]">/ 100</span>
        </div>

        <ChevronDown
          size={16}
          className={`shrink-0 text-[--text-tertiary] mt-1.5 transition-transform duration-200 ${
            expanded ? "rotate-180" : ""
          }`}
        />
      </button>

      {expanded && (
        <div className="px-4 sm:px-5 pb-4 sm:pb-5 pt-0 border-t border-[--border-subtle] mt-0">
          <div className="pt-4 space-y-3">
            <p className="text-sm text-[--text-secondary] leading-relaxed">
              {idea.description}
            </p>
            {Array.isArray(idea.agent_thinking) && idea.agent_thinking.length > 0 && (
              <div className="rounded-[10px] border border-indigo-500/20 bg-indigo-500/5 p-3">
                <p className="text-[11px] uppercase tracking-wide text-indigo-300 mb-2">What agents are thinking</p>
                <ul className="space-y-1.5">
                  {idea.agent_thinking.slice(0, 3).map((thought, idx) => (
                    <li key={`${idea.id}-thought-${idx}`} className="text-xs text-[--text-secondary] leading-relaxed">
                      • {thought}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex items-center justify-end">
              <Link
                href={`/new?idea=${encodeURIComponent(buildSimulateIdeaPrefill(idea))}`}
                className="inline-flex items-center gap-2 rounded-[10px] bg-[--accent-primary] text-white px-3.5 py-2 text-xs font-medium hover:opacity-90 transition-opacity"
              >
                Simulate with your tweaks
              </Link>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "Market Demand", score: idea.score_market_demand, icon: TrendingUp },
                { label: "Retention", score: idea.score_retention, icon: Shield },
                { label: "Virality", score: idea.score_virality, icon: Share2 },
                { label: "Feasibility", score: idea.score_feasibility, icon: Wrench },
              ].map(({ label, score, icon: Icon }) => (
                <div
                  key={label}
                  className="bg-[--bg-elevated] border border-[--border-subtle] rounded-[10px] p-3"
                >
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Icon size={13} className="text-[--text-tertiary]" />
                    <span className="text-[11px] text-[--text-tertiary]">{label}</span>
                  </div>
                  <div className="flex items-baseline gap-1">
                    <span className={`text-xl font-semibold tabular-nums ${ratingColor(score)}`}>
                      {score}
                    </span>
                    <span className="text-[10px] text-[--text-tertiary]">/ 100</span>
                  </div>
                  <div className="mt-2 h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        score >= 70 ? "bg-emerald-500" : score >= 45 ? "bg-amber-500" : "bg-red-500"
                      }`}
                      style={{ width: `${score}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function IdeasPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [ideas, setIdeas] = useState<PublishedIdea[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState(searchParams.get("category") || "");
  const [sort, setSort] = useState<"latest" | "rating">(
    (searchParams.get("sort") as "latest" | "rating") || "latest"
  );

  const resetFilters = () => {
    setCategory("");
    setSort("latest");
  };

  const fetchIdeas = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = { sort };
      if (category) params.category = category;
      const { data } = await api.get<PublishedIdeaList>("/api/ideas/", { params });
      setIdeas(data.ideas);
      setTotal(data.total);
    } catch {
      setError("Couldn't load ideas. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }, [category, sort]);

  useEffect(() => {
    void fetchIdeas();
  }, [fetchIdeas]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (sort !== "latest") params.set("sort", sort);
    const qs = params.toString();
    router.replace(`/ideas${qs ? `?${qs}` : ""}`, { scroll: false });
  }, [category, sort, router]);

  return (
    <main id="main-content" className="bg-void min-h-dvh pt-20">
      <Navbar />

      <div className="max-w-5xl mx-auto py-10 px-4">
        <div className="flex items-center justify-between gap-3 flex-wrap mb-6">
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-[12px] border border-[--border-subtle] bg-[--bg-surface] px-3.5 py-2 text-sm text-[--text-primary] hover:border-[--border-default] transition-colors"
          >
            <ArrowLeft size={14} />
            Back to home
          </Link>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={resetFilters}
              className="inline-flex items-center gap-2 rounded-[12px] border border-[--border-subtle] bg-[--bg-surface] px-3.5 py-2 text-sm text-[--text-primary] hover:border-[--border-default] transition-colors"
            >
              <RefreshCw size={14} />
              Reset filters
            </button>
            <Link
              href="/new"
              className="inline-flex items-center gap-2 rounded-[12px] bg-[--accent-primary] px-3.5 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
            >
              <Plus size={14} />
              New simulation
            </Link>
          </div>
        </div>

        <div className="mb-8 space-y-4">

          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-[12px] bg-indigo-500/15 flex items-center justify-center">
              <Lightbulb size={20} className="text-indigo-400" />
            </div>
            <div>
              <h1 className="text-h2 font-medium text-[--text-primary]">Ideas Dashboard</h1>
              <p className="text-sm text-[--text-tertiary]">
                {total > 0 ? `${total} idea${total !== 1 ? "s" : ""} published` : "Community-published simulation ideas"}
              </p>
            </div>
          </div>

          <p className="text-sm text-[--text-secondary] max-w-2xl">
            Browse the public feed, open an idea for details, or launch a faster, lower-cost simulation run with dual validation (macro context + statistical checks).
          </p>
        </div>

        <div className="flex items-center gap-3 mb-6 flex-wrap">
          <div className="relative">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="appearance-none bg-[--bg-surface] border border-[--border-default] rounded-[10px] px-3 py-2 pr-8 text-sm text-[--text-primary] cursor-pointer hover:border-[--border-strong] transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
            <ChevronDown
              size={14}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[--text-tertiary] pointer-events-none"
            />
          </div>

          <button
            onClick={() => setSort(sort === "latest" ? "rating" : "latest")}
            className="flex items-center gap-1.5 bg-[--bg-surface] border border-[--border-default] rounded-[10px] px-3 py-2 text-sm text-[--text-primary] cursor-pointer hover:border-[--border-strong] transition-colors"
          >
            <ArrowUpDown size={14} className="text-[--text-tertiary]" />
            {sort === "latest" ? "Latest" : "Top Rated"}
          </button>
        </div>

        {loading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="border border-[--border-subtle] rounded-[14px] bg-[--bg-surface] p-5 animate-pulse"
              >
                <div className="flex items-start gap-4">
                  <div className="w-9 h-9 rounded-full bg-white/5" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-white/5 rounded w-48" />
                    <div className="h-3 bg-white/5 rounded w-32" />
                    <div className="h-3 bg-white/5 rounded w-full" />
                  </div>
                  <div className="w-16 h-10 rounded-[10px] bg-white/5" />
                </div>
              </div>
            ))}
          </div>
        )}

        {error && <ErrorState message={error} onRetry={() => void fetchIdeas()} />}

        {!loading && !error && ideas.length === 0 && (
          <div className="text-center py-16">
            <Lightbulb size={40} className="mx-auto text-[--text-tertiary] mb-4 opacity-40" />
            <h3 className="text-sm font-medium text-[--text-secondary] mb-1">No ideas published yet</h3>
            <p className="text-xs text-[--text-tertiary]">
              Run a simulation and publish your idea to see it here.
            </p>
          </div>
        )}

        {!loading && !error && ideas.length > 0 && (
          <div className="space-y-3">
            {ideas.map((idea) => (
              <IdeaRow key={idea.id} idea={idea} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
