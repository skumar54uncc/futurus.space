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

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <div className="flex items-start justify-between mb-8 gap-4 flex-wrap">
        <div>
          <h1 className="text-h2 font-medium text-[--text-primary]">
            {getGreeting()}
            {user?.firstName ? `, ${user.firstName}` : ""}.
          </h1>
          <p className="text-sm text-[--text-tertiary] mt-1">
            {!loading && !error && simulations.length > 0
              ? `${simulations.length} simulation${simulations.length !== 1 ? "s" : ""} total`
              : "Run your first simulation below."}
          </p>
        </div>
      </div>

      <div className="space-y-6" role="list" aria-label="Your simulations" aria-live="polite">
        <Link href="/new" className="block">
          <div className="rounded-[16px] border-2 border-dashed border-[--border-accent] bg-[--accent-primary-muted] p-6 flex items-center gap-4 transition-all duration-200 hover:border-[--accent-primary] hover:bg-[rgba(99,102,241,0.15)] hover:-translate-y-0.5 group cursor-pointer">
            <div className="w-10 h-10 rounded-[10px] bg-[--accent-primary] flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
              <Plus size={20} className="text-white" />
            </div>
            <div>
              <p className="font-medium text-[--text-primary] text-sm">New simulation</p>
              <p className="text-xs text-[--text-tertiary] mt-0.5">Describe any idea to get started →</p>
            </div>
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
