"use client";

import { PenLine, Network, Eye } from "lucide-react";
import { useInView } from "@/hooks/useInView";

const steps = [
  {
    icon: PenLine,
    title: "Write your idea",
    description:
      "Describe it however you want. No forms, no jargon, no business terminology. Just words.",
  },
  {
    icon: Network,
    title: "Up to a thousand minds react",
    description:
      "Futurus spawns up to 1,000 AI agents — each with personality, memory, and decision logic — so your idea is stress-tested like a synthetic market.",
  },
  {
    icon: Eye,
    title: "See the future",
    description:
      "Get a detailed report: adoption curves, failure points, who loves it, who doesn't, and what to change.",
  },
];

function StepCard({ step, index }: { step: (typeof steps)[0]; index: number }) {
  const { ref, inView } = useInView();
  return (
    <div
      ref={ref}
      className={`glass glass-hover rounded-2xl p-8 transition-all duration-500 group ${
        inView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-5"
      }`}
    >
      <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-6 group-hover:bg-indigo-500/20 transition-colors">
        <step.icon className="w-5 h-5 text-indigo-400" />
      </div>
      <div className="text-xs text-slate-600 font-medium uppercase tracking-widest mb-3">Step {index + 1}</div>
      <h3 className="text-lg font-medium text-white mb-3">{step.title}</h3>
      <p className="text-sm text-slate-400 leading-relaxed">{step.description}</p>
    </div>
  );
}

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 relative">
      <div className="max-w-5xl mx-auto px-4">
        <h2 className="text-3xl font-serif italic text-center text-white mb-4">Three steps to certainty</h2>
        <p className="text-center text-slate-500 mb-16 max-w-md mx-auto">
          From raw idea to detailed forecast in minutes.
        </p>

        <div className="grid md:grid-cols-3 gap-6">
          {steps.map((step, i) => (
            <StepCard key={step.title} step={step} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
