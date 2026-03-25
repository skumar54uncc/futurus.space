"use client";
import { LiveEvent } from "@/lib/types";

const typeColors: Record<string, string> = {
  adopted: "text-emerald-400",
  churned: "text-amber-400",
  referred: "text-sky-400",
  rejected: "text-red-400",
};

const typeLabels: Record<string, string> = {
  adopted: "Adopted",
  churned: "Churned",
  referred: "Referred",
  rejected: "Rejected",
};

function maxLoggedTurn(events: LiveEvent[]): number {
  if (!events.length) return 0;
  return Math.max(0, ...events.map((e) => e.turn ?? 0));
}

export function SimulationActivityLog({
  events,
  engineTurn = 0,
}: {
  events: LiveEvent[];
  /** Live turn counter from WebSocket / API (can be ahead when a tick has no logged actions). */
  engineTurn?: number;
}) {
  const newestLoggedTurn = maxLoggedTurn(events);
  const showQuietHint =
    engineTurn > 0 && newestLoggedTurn > 0 && engineTurn > newestLoggedTurn;

  return (
    <div className="p-6 font-mono text-[13px] space-y-2.5 min-h-[280px] max-h-[380px] overflow-y-auto scroll-smooth">
      {events.length === 0 && (
        <div className="py-12 text-center text-slate-500 text-sm">
          Waiting for agent activity&hellip; updates sync from the server every couple of seconds.
        </div>
      )}
      {showQuietHint && (
        <p className="text-[11px] text-slate-500 leading-relaxed border-b border-white/5 pb-2 mb-1">
          The counter can show turn {engineTurn} while the newest line is still turn {newestLoggedTurn}. That usually means
          the latest tick had no sampled agent actions (normal with many agents), or the list is still catching up.
        </p>
      )}
      {events.map((e, i) => (
        <div
          key={e.id ?? `${e.turn}-${e.agent_name}-${i}-${e.description?.slice(0, 16)}`}
          className={`flex flex-wrap gap-x-1 gap-y-0.5 items-baseline transition-opacity duration-150 ${
            i === 0 ? "opacity-100" : "opacity-[0.72]"
          }`}
        >
          <span className="text-slate-600 shrink-0">Turn {e.turn ?? "—"}</span>
          <span className="text-slate-500 shrink-0">·</span>
          <span className="text-slate-400 shrink-0">{e.agent_name}</span>
          <span className="text-slate-500 shrink-0">·</span>
          <span className={`${typeColors[e.event_type] ?? "text-slate-400"} shrink-0 capitalize`}>
            {typeLabels[e.event_type] ?? e.event_type}
          </span>
          <span className="text-slate-600">
            &mdash; &ldquo;{e.description || "—"}&rdquo;
          </span>
        </div>
      ))}
      {events.length > 0 && (
        <span className="inline-block w-2 h-4 bg-indigo-400/60 animate-pulse align-middle ml-0.5" />
      )}
    </div>
  );
}
