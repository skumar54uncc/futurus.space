"use client";

import { PenLine, Network, BarChart3 } from "lucide-react";
import { useInView } from "@/hooks/useInView";

const steps = [
  {
    icon: PenLine,
    num: "01",
    title: "Write your idea",
    description:
      "Describe it however you want — no forms, no jargon. Just plain English. Futurus extracts your target market, pricing, and assumptions automatically.",
    detail: "Takes 30 seconds",
  },
  {
    icon: Network,
    num: "02",
    title: "A thousand minds react",
    description:
      "Futurus spawns up to 1,000 AI agents — each with distinct personality, memory, and decision logic — stress-testing your idea like a real synthetic market.",
    detail: "Runs in minutes",
  },
  {
    icon: BarChart3,
    num: "03",
    title: "Read the verdict",
    description:
      "A full report surfaces adoption curves, failure points, segment-level breakdown, risk matrix, and pivot suggestions grounded in the simulation data.",
    detail: "6-section report",
  },
];

function StepCard({ step, index }: { step: (typeof steps)[0]; index: number }) {
  const { ref, inView } = useInView();
  return (
    <div
      ref={ref}
      className={`relative glass glass-hover rounded-2xl p-8 transition-all duration-500 group ${
        inView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
      }`}
      style={{ transitionDelay: `${index * 100}ms` }}
    >
      {/* Large faded step number */}
      <div
        className="absolute top-6 right-6 font-mono text-5xl font-bold leading-none select-none pointer-events-none"
        style={{ color: "rgba(99,102,241,0.07)" }}
        aria-hidden
      >
        {step.num}
      </div>

      <div className="w-11 h-11 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-6 group-hover:bg-indigo-500/20 group-hover:border-indigo-500/40 transition-all duration-200">
        <step.icon className="w-5 h-5 text-indigo-400" />
      </div>

      <div className="text-[10px] font-semibold text-indigo-500 uppercase tracking-[0.14em] mb-2">
        Step {step.num}
      </div>
      <h3 className="text-lg font-medium text-white mb-3 leading-snug">{step.title}</h3>
      <p className="text-sm text-slate-400 leading-relaxed mb-5">{step.description}</p>

      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.07]">
        <span className="w-1.5 h-1.5 rounded-full bg-indigo-400/60" />
        <span className="text-[11px] text-slate-500">{step.detail}</span>
      </div>
    </div>
  );
}

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 relative">
      <div className="max-w-5xl mx-auto px-4">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/[0.08] text-[11px] text-slate-500 uppercase tracking-widest mb-6">
            How it works
          </div>
          <h2 className="text-3xl sm:text-4xl font-serif italic text-white mb-4">Three steps to certainty</h2>
          <p className="text-slate-500 max-w-sm mx-auto text-sm leading-relaxed">
            From raw idea to detailed market forecast — in minutes, not months.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          {steps.map((step, i) => (
            <StepCard key={step.title} step={step} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
