"use client";

import { AdoptionPoint } from "@/lib/types";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface Props {
  data: AdoptionPoint[];
}

const tooltipStyle = {
  background: "var(--bg-elevated)",
  border: "1px solid var(--border-default)",
  borderRadius: "10px",
  color: "var(--text-primary)",
  fontSize: "12px",
};

export function AdoptionCurveChart({ data }: Props) {
  const peakMonth = data.reduce((max, d) => (d.net > (max?.net ?? 0) ? d : max), data[0]);

  return (
    <div className="border border-[--border-subtle] rounded-xl p-6 bg-[--bg-surface]/50">
      <h2 className="text-base font-medium mb-1 text-[--text-primary]">Adoption curve</h2>
      <p className="text-sm text-muted-foreground mb-6">
        How your customer base grows (and churns) over the simulation period
      </p>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 4, right: 20, left: 0, bottom: 0 }} style={{ background: "transparent" }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="month_equivalent"
            label={{ value: "Month", position: "insideBottom", offset: -2, fill: "var(--text-tertiary)" }}
            tickFormatter={(v) => `M${v}`}
            tick={{ fontSize: 12, fill: "#94a3b8" }}
          />
          <YAxis tick={{ fontSize: 12, fill: "#94a3b8" }} />
          <Tooltip
            formatter={(value: number, name: string) => [value.toLocaleString(), name]}
            labelFormatter={(label) => `Month ${label}`}
            contentStyle={tooltipStyle}
          />
          <Legend wrapperStyle={{ color: "var(--text-secondary)", fontSize: 12 }} />
          {peakMonth && (
            <ReferenceLine
              x={peakMonth.month_equivalent}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              label={{ value: "Peak growth", fontSize: 11, fill: "#f59e0b" }}
            />
          )}
          <Line
            type="monotone"
            dataKey="cumulative"
            name="Total customers"
            stroke="#34d399"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="adopters"
            name="New adoptions"
            stroke="#818cf8"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="5 5"
          />
          <Line
            type="monotone"
            dataKey="churned"
            name="Churned"
            stroke="#f87171"
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="3 3"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
