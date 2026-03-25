"use client";
import { useEffect, useState } from "react";
import { FreeTierLimitsNotice } from "@/components/landing/FreeTierLimitsNotice";
import { OPEN_ACCESS_AGENT_CAP, OPEN_ACCESS_TURN_CAP } from "@/lib/simulationLimits";

const events = [
  { turn: 12, agent: "Pragmatist_Sarah", type: "adopted" as const, text: "Finally, something that actually works" },
  { turn: 12, agent: "PriceShopper_Alex", type: "rejected" as const, text: "Too expensive for my budget" },
  { turn: 13, agent: "EarlyAdopter_Marco", type: "referred" as const, text: "Told 3 colleagues about it" },
  { turn: 13, agent: "PowerUser_Priya", type: "adopted" as const, text: "Deep feature set, love it" },
  { turn: 14, agent: "Student_Jay", type: "adopted" as const, text: "Free tier is perfect for me" },
  { turn: 14, agent: "Skeptic_Linda", type: "rejected" as const, text: "Not sure I trust a new brand" },
  { turn: 15, agent: "Creator_Zoe", type: "referred" as const, text: "Posted about it on Twitter" },
  { turn: 15, agent: "BudgetBuyer_Raj", type: "adopted" as const, text: "Great value for the price" },
  { turn: 16, agent: "Corporate_Mike", type: "adopted" as const, text: "Fits our team workflow perfectly" },
  { turn: 16, agent: "Loyalist_Emma", type: "churned" as const, text: "Found a cheaper alternative" },
];

const typeColors: Record<string, string> = {
  adopted: "text-emerald-400",
  rejected: "text-red-400",
  referred: "text-blue-400",
  churned: "text-amber-400",
};

export function LivePreview() {
  const [visibleCount, setVisibleCount] = useState(0);
  const [progress, setProgress] = useState(33);

  useEffect(() => {
    const interval = setInterval(() => {
      setVisibleCount((c) => {
        if (c >= events.length) return 0;
        return c + 1;
      });
      setProgress((p) => {
        if (p >= 85) return 33;
        return p + Math.random() * 3 + 1;
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const visibleEvents = events.slice(0, visibleCount);

  return (
    <section className="py-24 relative">
      <div className="max-w-3xl mx-auto px-4">
        <h2 className="text-3xl font-serif italic text-center text-white mb-4">
          Watch ideas come alive
        </h2>
        <p className="text-center text-slate-500 mb-8 max-w-lg mx-auto">
          Real-time simulation of AI agents reacting to an idea — up to {OPEN_ACCESS_AGENT_CAP.toLocaleString()} agents and{" "}
          {OPEN_ACCESS_TURN_CAP} turns per run on this deployment.
        </p>

        <div className="glass rounded-2xl overflow-hidden">
          {/* Header bar */}
          <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-sm text-slate-300 font-medium">Live simulation</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-500 font-mono">
              <span>612 agents active</span>
              <span>Turn {events[Math.min(visibleCount, events.length - 1)]?.turn || 12} of 40</span>
            </div>
          </div>

          {/* Progress bar */}
          <div className="h-0.5 bg-white/5">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-cyan-500 transition-all duration-1000"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Event feed */}
          <div className="p-6 font-mono text-[13px] space-y-2.5 min-h-[280px]">
            {visibleEvents.map((e, i) => (
              <div
                key={i}
                className="flex gap-3 animate-[fadeIn_0.5s_ease-out]"
                style={{ opacity: i === visibleEvents.length - 1 ? 0.9 : 0.6 }}
              >
                <span className="text-slate-600 shrink-0">Turn {e.turn}</span>
                <span className="text-slate-500 shrink-0">·</span>
                <span className="text-slate-400 shrink-0">{e.agent}</span>
                <span className="text-slate-500 shrink-0">·</span>
                <span className={`${typeColors[e.type]} capitalize shrink-0`}>{e.type}</span>
                <span className="text-slate-600">&mdash; &ldquo;{e.text}&rdquo;</span>
              </div>
            ))}
            {visibleCount > 0 && (
              <span className="inline-block w-2 h-4 bg-indigo-400/60 animate-blink" />
            )}
          </div>
        </div>

        <div className="mt-8 max-w-2xl mx-auto">
          <FreeTierLimitsNotice />
        </div>
      </div>
    </section>
  );
}
