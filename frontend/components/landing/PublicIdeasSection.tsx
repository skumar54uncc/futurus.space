import Link from "next/link";
import { ArrowRight, Lightbulb, Star, Wrench, TrendingUp, Shield, Share2 } from "lucide-react";
import type { PublishedIdea, PublishedIdeaList } from "@/lib/types";

function ratingColor(score: number): string {
  if (score >= 70) return "text-emerald-400";
  if (score >= 45) return "text-amber-400";
  return "text-red-400";
}

function scoreBarColor(score: number): string {
  if (score >= 70) return "bg-emerald-500";
  if (score >= 45) return "bg-amber-500";
  return "bg-red-500";
}

function buildSimulateIdeaPrefill(idea: PublishedIdea): string {
  const merged = `${idea.title}: ${idea.description}`.trim();
  return merged.length > 500 ? `${merged.slice(0, 500)}...` : merged;
}

async function fetchPublicIdeas(): Promise<PublishedIdea[]> {
  const base = (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
  try {
    const res = await fetch(`${base}/api/ideas/?sort=rating&limit=3`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = (await res.json()) as PublishedIdeaList;
    return Array.isArray(data.ideas) ? data.ideas : [];
  } catch {
    return [];
  }
}

function Score({ label, score, icon: Icon }: { label: string; score: number; icon: React.ElementType }) {
  return (
    <div className="rounded-[12px] border border-[--border-subtle] bg-[--bg-elevated] p-3">
      <div className="flex items-center gap-1.5 mb-1 text-[--text-tertiary] text-[11px]">
        <Icon size={12} />
        {label}
      </div>
      <div className="flex items-baseline gap-1">
        <span className={`text-base font-semibold tabular-nums ${ratingColor(score)}`}>{score}</span>
        <span className="text-[10px] text-[--text-tertiary]">/100</span>
      </div>
      <div className="mt-2 h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div className={`h-full rounded-full ${scoreBarColor(score)}`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

export async function PublicIdeasSection() {
  const ideas = await fetchPublicIdeas();
  const hasIdeas = ideas.length > 0;

  return (
    <section className="max-w-6xl mx-auto px-4 py-16">
      <div className="flex items-center justify-between gap-4 mb-8 flex-wrap">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-[--text-tertiary] mb-2">Community Ideas</p>
          <h2 className="text-h2 font-medium text-[--text-primary]">Public Ideas Dashboard</h2>
          <p className="text-sm text-[--text-tertiary] mt-1">See top-rated ideas, then run your own improved version with faster, low-cost simulation defaults and stronger validation.</p>
        </div>
        <Link
          href="/ideas"
          className="inline-flex items-center gap-2 rounded-[12px] border border-[--border-subtle] bg-[--bg-surface] px-4 py-2.5 text-sm text-[--text-primary] hover:border-[--border-default] transition-colors"
        >
          Browse all ideas
          <ArrowRight size={15} />
        </Link>
      </div>

      {!hasIdeas && (
        <div className="rounded-[16px] border border-[--border-subtle] bg-[--bg-surface] p-8 text-center">
          <Lightbulb size={28} className="mx-auto text-[--text-tertiary] opacity-60 mb-3" />
          <p className="text-sm text-[--text-secondary]">No public ideas yet.</p>
          <p className="text-xs text-[--text-tertiary] mt-1">Publish a simulation report to appear here.</p>
        </div>
      )}

      {hasIdeas && (
        <div className="grid gap-4 md:grid-cols-3">
          {ideas.map((idea) => {
            const prefill = buildSimulateIdeaPrefill(idea);
            return (
              <article key={idea.id} className="rounded-[16px] border border-[--border-subtle] bg-[--bg-surface] p-4 flex flex-col">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <span className="text-[10px] px-2 py-1 rounded-full border border-indigo-500/25 bg-indigo-500/10 text-indigo-300">
                    {idea.category}
                  </span>
                  <div className="inline-flex items-center gap-1.5">
                    <Star size={13} className={ratingColor(idea.overall_rating)} />
                    <span className={`text-sm font-semibold tabular-nums ${ratingColor(idea.overall_rating)}`}>
                      {idea.overall_rating}/100
                    </span>
                  </div>
                </div>

                <h3 className="text-sm font-semibold text-[--text-primary] mb-1 line-clamp-1">{idea.title}</h3>
                <p className="text-xs text-[--text-tertiary] mb-3">by {idea.user_name}</p>
                <p className="text-sm text-[--text-secondary] leading-relaxed line-clamp-3 min-h-[3.9rem]">{idea.description}</p>

                {Array.isArray(idea.agent_thinking) && idea.agent_thinking.length > 0 && (
                  <div className="mt-3 rounded-[10px] border border-indigo-500/20 bg-indigo-500/5 p-2.5">
                    <p className="text-[10px] uppercase tracking-wide text-indigo-300 mb-1.5">Agent thinking</p>
                    <p className="text-xs text-[--text-secondary] line-clamp-2">{idea.agent_thinking[0]}</p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2 mt-4">
                  <Score label="Demand" score={idea.score_market_demand} icon={TrendingUp} />
                  <Score label="Retention" score={idea.score_retention} icon={Shield} />
                  <Score label="Virality" score={idea.score_virality} icon={Share2} />
                  <Score label="Feasibility" score={idea.score_feasibility} icon={Wrench} />
                </div>

                <Link
                  href={`/new?idea=${encodeURIComponent(prefill)}`}
                  className="mt-4 inline-flex items-center justify-center gap-2 rounded-[12px] bg-[--accent-primary] text-white text-sm font-medium py-2.5 px-3 hover:opacity-90 transition-opacity"
                >
                  Simulate with your tweaks
                  <ArrowRight size={14} />
                </Link>
                <p className="mt-2 text-[10px] text-[--text-tertiary] text-center">
                  You can edit the idea before launching simulation.
                </p>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
