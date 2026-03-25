"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import { Simulation } from "@/lib/types";

const TERMINAL = new Set<Simulation["status"]>(["completed", "failed"]);

export function useSimulation(simulationId: string, options?: { pollMs?: number }) {
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pollMs = options?.pollMs ?? 0;
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get<Simulation>(`/api/simulations/${simulationId}`);
      if (mounted.current) {
        setSimulation(data);
        setError(null);
      }
      return data;
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } } };
      const msg = ax.response?.data?.detail || "Failed to load simulation";
      if (mounted.current) setError(typeof msg === "string" ? msg : "Failed to load simulation");
      return null;
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [simulationId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!pollMs || !simulation || TERMINAL.has(simulation.status)) return;
    const id = window.setInterval(() => {
      refresh();
    }, pollMs);
    return () => window.clearInterval(id);
  }, [pollMs, simulation?.status, refresh]);

  return { simulation, loading, error, refresh };
}
