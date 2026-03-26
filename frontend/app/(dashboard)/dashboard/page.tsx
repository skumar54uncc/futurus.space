"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useUser } from "@clerk/nextjs";
import { Plus, FlaskConical } from "lucide-react";
import { api } from "@/lib/api";
import { simulationIdKey } from "@/lib/simulationId";
import type { Simulation } from "@/lib/types";
import { SimulationCard } from "@/components/dashboard/SimulationCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { SimulationCardSkeleton } from "@/components/ui/skeleton";

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useUser();
  const [simulations, setSimulations] = useState<Simulation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSimulations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get<Simulation[]>("/api/simulations/");
      const list = Array.isArray(data) ? data : [];
      const byId = new Map<string, Simulation>();
      for (const s of list) {
        const k = simulationIdKey(s.id);
        if (!k) continue;
        if (!byId.has(k)) byId.set(k, { ...s, id: k });
      }
      setSimulations(Array.from(byId.values()));
    } catch {
      setError("Couldn't load your simulations. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  /** Merge server row after revoke/update — stable id match + spread so we never leave a stale card. */
  const mergeSimulationFromServer = useCallback((updated: Simulation) => {
    const key = simulationIdKey(updated.id);
    if (!key) return;
    setSimulations((prev) =>
      prev.map((s) => (simulationIdKey(s.id) === key ? { ...s, ...updated, id: key } : s))
    );
  }, []);

  useEffect(() => {
    void fetchSimulations();
  }, [fetchSimulations]);

  const completedCount = simulations.filter((s) => s.status === "completed").length;
  const runningCount = simulations.filter((s) =>
    ["queued", "building_seed", "generating_personas", "running", "generating_report"].includes(s.status)
  ).length;

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-h2 font-medium text-[--text-primary]">
          {getGreeting()}
          {user?.firstName ? `, ${user.firstName}` : ""}.
        </h1>
        <p className="text-sm text-[--text-tertiary] mt-1">
          {!loading && !error && simulations.length > 0
            ? `${simulations.length} simulation${simulations.length !== 1 ? "s" : ""} total`
            : "Your simulations will appear here once you run one."}
        </p>

        {!loading && !error && simulations.length > 0 && (
          <div className="flex items-center gap-4 mt-5 flex-wrap">
            {[
              { label: "Total", value: simulations.length, color: "text-[--text-primary]" },
              { label: "Completed", value: completedCount, color: "text-emerald-400" },
              { label: "Running", value: runningCount, color: "text-indigo-400" },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex items-center gap-2 bg-[--bg-surface] border border-[--border-subtle] rounded-xl px-4 py-2.5">
                <span className={`text-lg font-medium tabular-nums ${color}`}>{value}</span>
                <span className="text-xs text-[--text-tertiary]">{label}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-6" role="list" aria-label="Your simulations" aria-live="polite">
        <Link href="/new" className="block group">
          <div className="rounded-[16px] border border-dashed border-[--border-accent] bg-[--accent-primary-muted] p-5 flex items-center gap-4 transition-all duration-200 hover:border-indigo-500/60 hover:bg-[rgba(99,102,241,0.15)] hover:-translate-y-0.5 hover:shadow-[0_4px_24px_rgba(99,102,241,0.15)] cursor-pointer">
            <div className="w-10 h-10 rounded-[12px] bg-[--accent-primary] flex items-center justify-center shrink-0 group-hover:scale-105 group-hover:shadow-[0_0_20px_rgba(99,102,241,0.5)] transition-all duration-200">
              <Plus size={18} className="text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-[--text-primary] text-sm">New simulation</p>
              <p className="text-xs text-[--text-tertiary] mt-0.5">Describe any idea — get a full market report</p>
            </div>
            <span className="text-[--text-tertiary] group-hover:text-indigo-400 transition-colors text-sm">&#8594;</span>
          </div>
        </Link>

        {loading && (
          <div className="space-y-3 stagger">
            <SimulationCardSkeleton />
            <SimulationCardSkeleton />
            <SimulationCardSkeleton />
          </div>
        )}

        {error && (
          <ErrorState message={error} onRetry={() => void fetchSimulations()} />
        )}

        {!loading && !error && simulations.length === 0 && (
          <EmptyState
            icon={FlaskConical}
            title="No simulations yet"
            description="Describe any idea to run your first simulation. Takes a few minutes."
            action={{
              label: "Run your first simulation",
              onClick: () => router.push("/new"),
              icon: <Plus size={14} />,
            }}
          />
        )}

        {!loading && !error && simulations.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 stagger items-stretch">
            {simulations.map((sim) => (
              <div key={sim.id} className="h-full min-h-0 flex" role="listitem">
                <SimulationCard
                  sim={sim}
                  onDeleted={(id) =>
                    setSimulations((prev) => prev.filter((s) => simulationIdKey(s.id) !== simulationIdKey(id)))
                  }
                  onUpdated={mergeSimulationFromServer}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
