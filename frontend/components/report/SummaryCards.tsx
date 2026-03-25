"use client";

import { SummaryMetrics } from "@/lib/types";
import { TrendingUp, TrendingDown, Users, Share2, Info } from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import { useCountUp } from "@/hooks/useCountUp";

interface Props {
  metrics: SummaryMetrics;
}

function AdoptionValue({ value }: { value: number }) {
  const n = useCountUp(value, 1200, 1);
  const color =
    value >= 35 ? "text-[#34d399]" : value >= 15 ? "text-[#fbbf24]" : "text-[#f87171]";
  return (
    <span className={`text-2xl font-semibold font-mono ${color}`}>
      {n}
      <span className="text-lg">%</span>
    </span>
  );
}

function ChurnValue({ value }: { value: number }) {
  const n = useCountUp(value, 1200, 1);
  const color = value < 10 ? "text-[#34d399]" : value < 25 ? "text-[#fbbf24]" : "text-[#f87171]";
  return (
    <span className={`text-2xl font-semibold font-mono ${color}`}>
      {n}
      <span className="text-lg">%</span>
    </span>
  );
}

function AdoptersValue({ value }: { value: number }) {
  const n = useCountUp(value, 1200, 0);
  return <span className="text-2xl font-semibold font-mono text-[#60a5fa]">{Math.round(n).toLocaleString()}</span>;
}

function ViralValue({ value }: { value: number }) {
  const n = useCountUp(value, 1200, 2);
  const color = value > 1 ? "text-[#34d399]" : "text-[#fbbf24]";
  return <span className={`text-2xl font-semibold font-mono ${color}`}>{n.toFixed(2)}</span>;
}

export function SummaryCards({ metrics }: Props) {
  const cards = [
    {
      label: "Adoption rate",
      icon: TrendingUp,
      tooltip:
        "The percentage of simulated customers who decided to try your product. Think of it like: out of everyone in your simulation who could adopt, this share actually did. Above 30% is great, 15-30% is average, below 15% needs work.",
      node: <AdoptionValue value={metrics.adoption_rate} />,
    },
    {
      label: "Churn rate",
      icon: TrendingDown,
      tooltip:
        "The percentage of customers who tried your product but then stopped using it or left. Lower is better. Under 10% means people love it and stay. Over 25% means many people try it once and don't come back.",
      node: <ChurnValue value={metrics.churn_rate} />,
    },
    {
      label: "Total adopters",
      icon: Users,
      tooltip:
        "The total number of simulated customers who became active users of your product by the end of the simulation. This represents your potential customer base after about 10 months of operation.",
      node: <AdoptersValue value={metrics.total_adopters} />,
    },
    {
      label: "Viral coefficient",
      icon: Share2,
      tooltip:
        "How many new customers each existing customer brings in through word-of-mouth or referrals. Above 1.0 means your product grows on its own (each customer brings more than one new customer). Below 1.0 means you'll need to keep spending on marketing to grow.",
      node: <ViralValue value={metrics.viral_coefficient} />,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div key={card.label} className="glass rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <card.icon className="h-4 w-4 text-[--text-accent]" />
            <span className="text-xs text-slate-500">{card.label}</span>
            <Tooltip content={card.tooltip}>
              <span className="inline-flex cursor-help">
                <Info className="h-3.5 w-3.5 text-slate-600" aria-hidden />
              </span>
            </Tooltip>
          </div>
          <div>{card.node}</div>
        </div>
      ))}
    </div>
  );
}
