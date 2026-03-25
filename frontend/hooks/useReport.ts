"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Report, Simulation } from "@/lib/types";

export function useReport(simulationId: string) {
  const [report, setReport] = useState<Report | null>(null);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetchData = async () => {
      try {
        const [reportRes, simRes] = await Promise.all([
          api.get(`/api/reports/${simulationId}`),
          api.get(`/api/simulations/${simulationId}`),
        ]);
        if (mounted) {
          setReport(reportRes.data);
          setSimulation(simRes.data);
          setError(null);
        }
      } catch (err: unknown) {
        const ax = err as { response?: { data?: { detail?: string } } };
        if (mounted) setError(ax?.response?.data?.detail || "Failed to load report");
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchData();
    return () => { mounted = false; };
  }, [simulationId]);

  return { report, simulation, loading, error };
}
