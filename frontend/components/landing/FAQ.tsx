"use client";

import * as Accordion from "@radix-ui/react-accordion";
import { ChevronDown } from "lucide-react";

const FAQS = [
  {
    q: "How is this different from a spreadsheet model?",
    a: "A spreadsheet reflects your assumptions. Futurus runs thousands of simulated people with distinct personalities, budgets, and decision logic who react to your idea — surfacing failure modes you didn't think to model.",
  },
  {
    q: "How accurate are the simulations?",
    a: "No simulation is a guarantee. Futurus is a thinking tool — it helps you stress-test assumptions and discover blind spots before you invest time and money. Accuracy improves when you provide detailed context.",
  },
  {
    q: "What LLM powers the simulation?",
    a: "Futurus uses a multi-tier LLM system. Key persona decisions use high-capability models; background agents use faster, cheaper models. This keeps simulations affordable while maintaining quality where it matters.",
  },
  {
    q: "Can I export the results?",
    a: "Yes. Every completed simulation includes a PDF report and a shareable link you can send to co-founders, investors, or advisors.",
  },
  {
    q: "Is my idea data kept private?",
    a: "Yes. Your idea data is only used to run your simulation and is never shared with other users, used for training, or sold. See our privacy policy for full details.",
  },
];

export function FAQ() {
  return (
    <section id="faq" className="max-w-[680px] mx-auto px-6 py-24">
      <p className="mono text-xs text-[--text-tertiary] uppercase tracking-widest mb-3">FAQ</p>
      <h2 className="text-h2 font-medium text-[--text-primary] mb-10">Common questions</h2>
      <Accordion.Root type="single" collapsible className="space-y-2">
        {FAQS.map(({ q, a }, i) => (
          <Accordion.Item
            key={i}
            value={`faq-${i}`}
            className="bg-[--bg-surface] border border-[--border-subtle] rounded-[12px] overflow-hidden"
          >
            <Accordion.Trigger className="w-full flex items-center justify-between px-5 py-4 text-sm font-medium text-[--text-primary] text-left hover:bg-[--bg-glass-hover] transition-colors group">
              {q}
              <ChevronDown
                size={16}
                className="text-[--text-tertiary] shrink-0 transition-transform duration-200 group-data-[state=open]:rotate-180"
                aria-hidden
              />
            </Accordion.Trigger>
            <Accordion.Content className="overflow-hidden data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up">
              <p className="px-5 pb-4 text-sm text-[--text-secondary] leading-relaxed">{a}</p>
            </Accordion.Content>
          </Accordion.Item>
        ))}
      </Accordion.Root>
    </section>
  );
}
