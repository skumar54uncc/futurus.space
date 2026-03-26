"use client";

import { AdoptionPoint } from "@/lib/types";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface Props {
  data: AdoptionPoint[];
}

const tooltipStyle = {
  background: "#1e1b2e",
  border: "1px solid rgba(99,102,241,0.25)",
  borderRadius: "10px",
  color: "#f1f5f9",
  fontSize: "13px",
  padding: "10px 14px",
};

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number; name: string; color: string }[]; label?: number }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={tooltipStyle}>
      <p className="font-medium mb-1.5 text-white">Month {label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="text-xs">
          {p.name}: <strong>{p.value.toLocaleString()}</strong>
        </p>
      ))}
    </div>
  );
}

export function AdoptionCurveChart({ data }: Props) {
  if (!data || data.length === 0) return null;

  const peakMonth = data.reduce((max, d) => (d.net > (max?.net ?? 0) ? d : max), data[0]);
  const finalCount = data[data.length - 1]?.cumulative ?? 0;
  const peakCount = Math.max(...data.map((d) => d.cumulative));

  return (
    <div className="border border-[--border-subtle] rounded-xl p-6 bg-[--bg-surface]/50">
      <div className="flex items-start justify-between mb-1 flex-wrap gap-2">
        <div>
          <h2 className="text-xl font-semibold text-[--text-primary]">Customer growth over time</h2>
          <p className="text-sm text-[--text-tertiary] mt-0.5">
            How your customer base grew — and how many left — across the simulation
          </p>
        </div>
        <div className="flex gap-4 shrink-0">
          <div className="text-right">
            <p className="text-lg font-bold text-[#34d399]">{peakCount.toLocaleString()}</p>
            <p className="text-xs text-[--text-tertiary]">Peak customers</p>
          </div>
          <div className="text-right">
            <p className="text-lg font-bold text-white">{finalCount.toLocaleString()}</p>
            <p className="text-xs text-[--text-tertiary]">Final customers</p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-5 mb-5 mt-3 flex-wrap">
        <span className="flex items-center gap-1.5 text-xs text-[--text-secondary]">
          <span className="w-3 h-0.5 rounded bg-[#34d399] inline-block" />
          Total customers (growing)
        </span>
        <span className="flex items-center gap-1.5 text-xs text-[--text-secondary]">
          <span className="w-3 h-0.5 rounded bg-[#f87171] inline-block" />
          Customers lost (churn)
        </span>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 16 }}>
          <defs>
            <linearGradient id="gradGreen" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#34d399" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#34d399" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="gradRed" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f87171" stopOpacity={0.18} />
              <stop offset="95%" stopColor="#f87171" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="month_equivalent"
            tickFormatter={(v) => `M${v}`}
            tick={{ fontSize: 11, fill: "#64748b" }}
            axisLine={false}
            tickLine={false}
            label={{ value: "Month", position: "insideBottom", offset: -8, fill: "#64748b", fontSize: 11 }}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#64748b" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v)}
          />
          <Tooltip content={<CustomTooltip />} />
          {peakMonth && (
            <ReferenceLine
              x={peakMonth.month_equivalent}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              strokeWidth={1.5}
              label={{ value: "📈 Peak", fontSize: 11, fill: "#f59e0b", position: "top" }}
            />
          )}
          <Area
            type="monotone"
            dataKey="cumulative"
            name="Total customers"
            stroke="#34d399"
            strokeWidth={2.5}
            fill="url(#gradGreen)"
            dot={false}
          />
          <Area
            type="monotone"
            dataKey="churned"
            name="Customers lost"
            stroke="#f87171"
            strokeWidth={1.5}
            fill="url(#gradRed)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
