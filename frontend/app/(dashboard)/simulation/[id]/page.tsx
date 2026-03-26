"use client";

import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Mail } from "lucide-react";
import * as AlertDialog from "@radix-ui/react-alert-dialog";
import toast from "react-hot-toast";
import { useSimulation } from "@/hooks/useSimulation";
import { useWebSocket, type WsMessage } from "@/hooks/useWebSocket";
import { SimulationActivityLog } from "@/components/simulation/SimulationActivityLog";
import { SimulationProgressBar } from "@/components/simulation/SimulationProgressBar";
import { LiveEvent, WebSocketMessage } from "@/lib/types";
import { simulationUiFromStatus } from "@/lib/simulationStatus";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/ErrorState";

const MAY_STILL_BE_ACTIVE = new Set([
  "queued",
  "building_seed",
  "generating_personas",
  "running",
  "generating_report",
]);

export default function SimulationPage() {
  const params = useParams();
  const router = useRouter();
  const simulationId = params.id as string;
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("Loading simulation…");
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [agentsActive, setAgentsActive] = useState(0);
  const [currentTurn, setCurrentTurn] = useState(0);
  const [maxTurns, setMaxTurns] = useState(0);
  const [agentTarget, setAgentTarget] = useState(0);
  const [revokeOpen, setRevokeOpen] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [notifyLoading, setNotifyLoading] = useState(false);
  const [notifyEnabled, setNotifyEnabled] = useState<boolean | null>(null);
  const redirected = useRef(false);

  const { simulation, loading, error, refresh } = useSimulation(simulationId, { pollMs: 2000 });

  const adoptionCount = useMemo(
    () => events.filter((e) => e.event_type === "adopted").length,
    [events]
  );

  const handleWsMessage = useCallback(
    (data: WsMessage) => {
      const msg = data as WebSocketMessage;
      if (msg.type === "progress") {
        setProgress((p) => Math.max(p, Math.max(0, msg.progress ?? 0)));
        if (msg.message) setStatusMessage(msg.message);
        if (msg.progress === 100 && msg.report_id) {
          if (!redirected.current) {
            redirected.current = true;
            setTimeout(() => router.push(`/simulation/${simulationId}/report`), 800);
          }
        }
        if (msg.progress === -1) {
          setStatusMessage("Simulation failed. Please try again.");
        }
      }
      if (msg.type === "turn") {
        setCurrentTurn((t) => Math.max(t, msg.turn || 0));
        setAgentsActive((a) => Math.max(a, msg.agents_active || 0));
        if (msg.max_turns) setMaxTurns(msg.max_turns);
        if (msg.agent_count) setAgentTarget(msg.agent_count);
        if (msg.progress !== undefined) {
          setProgress((p) => Math.max(p, Math.max(0, msg.progress ?? 0)));
        }
        if (msg.events?.length) {
          const turn = msg.turn ?? 0;
          setEvents((prev) => {
            const incoming: LiveEvent[] = msg.events!.map((e) => ({
              turn,
              agent_name: e.agent_name,
              segment: e.segment ?? "unknown",
              event_type: e.event_type,
              description: e.description ?? "",
            }));
            const key = (e: LiveEvent) =>
              `${e.turn}-${e.agent_name}-${e.event_type}-${(e.description || "").slice(0, 48)}`;
            const seen = new Set(prev.map(key));
            const fresh = incoming.filter((e) => !seen.has(key(e)));
            if (fresh.length === 0) return prev;
            return [...fresh, ...prev].slice(0, 100);
          });
        }
      }
    },
    [router, simulationId]
  );

  const { connected: wsConnected } = useWebSocket({
    simulationId,
    enabled: Boolean(simulationId),
    onMessage: handleWsMessage,
  });

  // Sync notify state from server on first load
  useEffect(() => {
    if (simulation && notifyEnabled === null) {
      setNotifyEnabled(simulation.notify_on_complete ?? false);
    }
  }, [simulation, notifyEnabled]);

  useEffect(() => {
    if (!simulation) return;
    setMaxTurns((m) => m || simulation.max_turns);
    setAgentTarget((a) => a || simulation.agent_count);
    setCurrentTurn((t) => Math.max(t, simulation.current_turn ?? 0));
    setAgentsActive((a) => Math.max(a, simulation.agents_active ?? 0));

    const ui = simulationUiFromStatus(simulation);
    setProgress((p) => Math.max(p, ui.progress));
    setStatusMessage(ui.message);

    if (simulation.status === "completed" && !redirected.current) {
      redirected.current = true;
      setTimeout(() => router.push(`/simulation/${simulationId}/report`), 500);
    }
  }, [simulation, simulationId, router]);

  useEffect(() => {
    let cancelled = false;
    const loadEvents = async () => {
      try {
        const { data } = await api.get<LiveEvent[]>(`/api/simulations/${simulationId}/events`, {
          params: { limit: 100 },
        });
        if (!cancelled) setEvents(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setEvents([]);
      }
    };
    loadEvents();
    const id = window.setInterval(loadEvents, 1200);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [simulationId]);

  const displayMaxTurns = maxTurns || simulation?.max_turns || 0;
  const displayAgentTarget = agentTarget || simulation?.agent_count || 0;

  async function toggleNotify() {
    setNotifyLoading(true);
    const sid = encodeURIComponent(String(simulationId).trim());
    try {
      const { data } = await api.post<{ notify_on_complete: boolean }>(`/api/simulations/${sid}/notify`);
      setNotifyEnabled(data.notify_on_complete);
      toast.success(
        data.notify_on_complete
          ? "You'll get an email when this simulation completes."
          : "Email notification removed."
      );
    } catch {
      toast.error("Couldn't update notification preference");
    } finally {
      setNotifyLoading(false);
    }
  }

  async function confirmRevoke() {
    setRevoking(true);
    const sid = encodeURIComponent(String(simulationId).trim());
    try {
      await api.post(`/api/simulations/${sid}/revoke`);
      setRevokeOpen(false);
      toast.success("Simulation stopped");
      await refresh();
    } catch (ax: unknown) {
      setRevokeOpen(false);
      const res = (ax as { response?: { data?: { detail?: unknown }; status?: number } })?.response;
      const d = res?.data?.detail;
      const msg =
        typeof d === "string"
          ? d
          : res?.status === 404
            ? "Simulation not found — try going back to the dashboard."
            : "Could not stop simulation";
      toast.error(msg);
    } finally {
      setRevoking(false);
    }
  }

  if (!loading && error) {
    return (
      <div className="max-w-lg mx-auto py-16 px-4">
        <ErrorState title="Simulation unavailable" message={error} onRetry={() => void refresh()} />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-2 text-sm text-[--text-secondary] hover:text-[--text-primary] transition-colors mb-6 -ml-1"
      >
        <ArrowLeft className="h-4 w-4 shrink-0" aria-hidden />
        Back to dashboard
      </Link>

      <div className="mb-6 text-center">
        <h1 className="text-h2 font-medium text-[--text-primary] mb-2">Watch ideas come alive</h1>
        <p className="text-[--text-tertiary] text-sm max-w-md mx-auto">
          {displayAgentTarget > 0
            ? `Real-time simulation of ${displayAgentTarget.toLocaleString()} AI agents.`
            : "Real-time simulation of AI agents reacting to your idea."}
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2 mb-8">
        {simulation && MAY_STILL_BE_ACTIVE.has(simulation.status) && (
          <Button variant="outline" size="sm" type="button" onClick={() => setRevokeOpen(true)}>
            Stop simulation
          </Button>
        )}
        {simulation && MAY_STILL_BE_ACTIVE.has(simulation.status) && (
          <Button
            variant={notifyEnabled ? "primary" : "secondary"}
            size="sm"
            type="button"
            loading={notifyLoading}
            icon={<Mail size={14} />}
            title={notifyEnabled ? "Click to cancel email notification" : "Email me when this simulation completes"}
            onClick={() => void toggleNotify()}
          >
            {notifyEnabled ? "Email on ✓" : "Email updates"}
          </Button>
        )}
      </div>

      <div aria-live="polite" aria-atomic="true" className="text-center text-[--text-secondary] text-sm mb-6 min-h-[3rem]">
        {simulation?.business_name ? (
          <span className="text-[--text-primary] font-medium block">{simulation.business_name}</span>
        ) : null}
        <span className="block text-[--text-tertiary] mt-1">{statusMessage}</span>
        {wsConnected && (
          <span className="block text-[11px] text-[--text-tertiary] mt-1 font-mono opacity-90">
            Live channel open
          </span>
        )}
      </div>

      <div className="mb-8">
        <SimulationProgressBar progress={progress} status={simulation?.status ?? "queued"} />
      </div>

      <div className="grid grid-cols-3 gap-3 max-w-[500px] mx-auto mb-8">
        <div className="bg-[--bg-surface] border border-[--border-subtle] rounded-[14px] p-4 text-center">
          <p className="font-mono font-bold text-xl text-[--text-primary]">
            {agentsActive > 0
              ? agentsActive.toLocaleString()
              : displayAgentTarget > 0
                ? displayAgentTarget.toLocaleString()
                : "—"}
          </p>
          <p className="text-xs text-[--text-tertiary] mt-1">Agents</p>
        </div>
        <div className="bg-[--bg-surface] border border-[--border-subtle] rounded-[14px] p-4 text-center">
          <p className="font-mono font-bold text-xl text-[--text-primary] tabular-nums">
            {displayMaxTurns > 0 ? `${currentTurn} / ${displayMaxTurns}` : "—"}
          </p>
          <p className="text-xs text-[--text-tertiary] mt-1">Turn</p>
        </div>
        <div className="bg-[--bg-surface] border border-[--border-subtle] rounded-[14px] p-4 text-center">
          <p className="font-mono font-bold text-xl text-[--text-primary]">{adoptionCount.toLocaleString()}</p>
          <p className="text-xs text-[--text-tertiary] mt-1">Adoptions (log)</p>
        </div>
      </div>

      <div className="rounded-2xl border border-[--border-default] bg-[--bg-surface] overflow-hidden shadow-lg shadow-black/10">
        <div className="px-6 py-4 border-b border-[--border-subtle] flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
            <span className="text-sm text-[--text-primary] font-medium">Live simulation</span>
          </div>
        </div>

        <SimulationActivityLog events={events} engineTurn={currentTurn || 0} />
      </div>

      <AlertDialog.Root
        open={revokeOpen}
        onOpenChange={(open) => {
          setRevokeOpen(open);
          if (!open) setRevoking(false);
        }}
      >
        <AlertDialog.Portal>
          <AlertDialog.Overlay className="fixed inset-0 bg-black/60 z-[500] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <AlertDialog.Content className="fixed z-[500] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-[400px] mx-4 bg-[--bg-elevated] border border-[--border-default] rounded-[16px] p-6 shadow-2xl animate-scale-in">
            <AlertDialog.Title className="text-base font-medium text-[--text-primary] mb-2">
              Stop this simulation?
            </AlertDialog.Title>
            <AlertDialog.Description className="text-sm text-[--text-secondary] mb-6">
              The run will stop and appear as Stopped on your dashboard.
            </AlertDialog.Description>
            <div className="flex justify-end gap-3">
              <Button variant="secondary" size="sm" type="button" onClick={() => setRevokeOpen(false)}>
                Cancel
              </Button>
              <Button variant="danger" size="sm" type="button" loading={revoking} onClick={() => void confirmRevoke()}>
                Stop run
              </Button>
            </div>
          </AlertDialog.Content>
        </AlertDialog.Portal>
      </AlertDialog.Root>
    </div>
  );
}
