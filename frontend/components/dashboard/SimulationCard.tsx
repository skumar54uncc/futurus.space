"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { formatDistanceToNow } from "date-fns";
import { MoreHorizontal, ExternalLink, Trash2, RotateCcw, Ban } from "lucide-react";
import * as AlertDialog from "@radix-ui/react-alert-dialog";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/button";
import { Badge, StatusBadge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/Tooltip";
import { api } from "@/lib/api";
import { simulationIdKey } from "@/lib/simulationId";
import type { Simulation } from "@/lib/types";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const MAY_STILL_BE_ACTIVE = new Set([
  "queued",
  "building_seed",
  "generating_personas",
  "running",
  "generating_report",
]);

const STOPPED_MSG = "Stopped by user";

/** Normalize idea text so line-clamp does not cut awkwardly on `---` separators. */
function cardIdeaExcerpt(raw: string): string {
  return raw
    .replace(/\s*---+(\s*|$)/g, " · ")
    .replace(/\s*·\s*(?:·\s*)+/g, " · ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[\s·—–-]+$/, "");
}

/** Ensure UUID string for API paths (avoids 404 from malformed IDs). */
function apiSimulationId(sim: Simulation): string {
  return simulationIdKey(sim.id);
}

function StatusRow({ sim }: { sim: Simulation }) {
  const stopped =
    sim.status === "revoked" ||
    (sim.status === "failed" && sim.error_message?.includes(STOPPED_MSG));
  if (stopped) {
    return (
      <Badge variant="secondary" dot={false}>
        Stopped
      </Badge>
    );
  }
  return <StatusBadge status={sim.status} />;
}

export interface SimulationCardProps {
  sim: Simulation;
  onDeleted: (id: string) => void;
  onUpdated: (sim: Simulation) => void;
}

/** Let the dropdown fully unmount before opening a modal AlertDialog (avoids stuck pointer-events / aria-hidden). */
const MENU_TO_DIALOG_MS = 80;

export function SimulationCard({ sim, onDeleted, onUpdated }: SimulationCardProps) {
  const router = useRouter();
  const [actionsMenuOpen, setActionsMenuOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [revokeOpen, setRevokeOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const dialogDelayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (dialogDelayTimerRef.current) clearTimeout(dialogDelayTimerRef.current);
    };
  }, []);

  function scheduleOpenAfterMenuCloses(setDialogOpen: (open: boolean) => void) {
    setActionsMenuOpen(false);
    if (dialogDelayTimerRef.current) clearTimeout(dialogDelayTimerRef.current);
    dialogDelayTimerRef.current = setTimeout(() => {
      dialogDelayTimerRef.current = null;
      setDialogOpen(true);
    }, MENU_TO_DIALOG_MS);
  }

  const progress = sim.max_turns > 0 ? (sim.current_turn / sim.max_turns) * 100 : 0;
  const isRunning = MAY_STILL_BE_ACTIVE.has(sim.status);
  const isCompleted = sim.status === "completed";
  const userStopped =
    sim.status === "revoked" ||
    (sim.status === "failed" && Boolean(sim.error_message?.includes(STOPPED_MSG)));
  const isFailed = sim.status === "failed" && !userStopped;
  const name = sim.business_name.length > 42 ? `${sim.business_name.slice(0, 42)}…` : sim.business_name;

  const sid = apiSimulationId(sim);
  const simHref = isCompleted ? `/simulation/${encodeURIComponent(sid)}/report` : `/simulation/${encodeURIComponent(sid)}`;

  async function confirmDelete() {
    setDeleting(true);
    try {
      await api.delete(`/api/simulations/${encodeURIComponent(sid)}`);
      onDeleted(sid);
      setDeleteOpen(false);
      toast.success("Simulation removed");
    } catch (ax: unknown) {
      console.error("Delete failed:", ax);
      setDeleteOpen(false);
      const msg = (ax as any)?.response?.data?.detail ?? "Could not complete. Try again.";
      toast.error(msg);
    } finally {
      setDeleting(false);
    }
  }

  async function confirmRevoke() {
    setRevoking(true);
    try {
      const { data } = await api.post<Simulation>(`/api/simulations/${encodeURIComponent(sid)}/revoke`);
      const next: Simulation = {
        ...sim,
        ...data,
        id: simulationIdKey(data.id ?? sim.id),
      };
      onUpdated(next);
      setRevokeOpen(false);
      toast.success("Simulation stopped");
    } catch (ax: unknown) {
      console.error("Revoke failed:", ax);
      setRevokeOpen(false);
      const msg = (ax as any)?.response?.data?.detail ?? "Could not complete. Try again.";
      toast.error(msg);
    } finally {
      setRevoking(false);
    }
  }

  return (
    <>
      <div
        className={`h-full w-full min-h-0 flex flex-col bg-[--bg-surface] border rounded-[16px] p-5 transition-all duration-300 hover:border-[--border-default] hover:-translate-y-0.5 hover:shadow-[0_4px_24px_rgba(0,0,0,0.3)] ${
          isFailed
            ? "border-[rgba(239,68,68,0.25)]"
            : isCompleted
              ? "border-[--border-default] hover:border-indigo-500/30"
              : isRunning
                ? "border-indigo-500/20 shadow-[0_0_0_1px_rgba(99,102,241,0.08)]"
                : "border-[--border-subtle]"
        }`}
      >
        {isRunning && (
          <div className="h-0.5 -mx-5 -mt-5 mb-5 rounded-t-[16px] overflow-hidden bg-[--bg-elevated]">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-indigo-400 transition-all duration-700 ease-out"
              style={{ width: `${Math.min(100, progress)}%` }}
            />
          </div>
        )}
        <div className="flex items-start justify-between gap-3 mb-3 shrink-0">
          <div className="flex-1 min-w-0">
            {sim.business_name.length > 42 ? (
              <Tooltip content={sim.business_name}>
                <h3 className="font-semibold text-[--text-primary] text-base truncate cursor-default leading-snug">{name}</h3>
              </Tooltip>
            ) : (
              <h3 className="font-semibold text-[--text-primary] text-base leading-snug">{name}</h3>
            )}
          </div>
          <StatusRow sim={sim} />
        </div>

        <p className="text-xs text-[--text-secondary] line-clamp-3 leading-relaxed">
          {cardIdeaExcerpt(sim.idea_description)}
        </p>

        <p className="text-xs text-[--text-tertiary] mt-4 mb-3 shrink-0">
          {sim.agent_count.toLocaleString()} agents · {sim.vertical} ·{" "}
          {formatDistanceToNow(new Date(sim.created_at), { addSuffix: true })}
        </p>

        {(isRunning || isFailed) && (
          <div className="mb-3 shrink-0">
            {isRunning && (
              <div>
                <div className="flex justify-between text-xs text-[--text-tertiary] mb-1.5">
                  <span>Turn {sim.current_turn} / {sim.max_turns}</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-[--bg-elevated] overflow-hidden">
                  <div
                    className="h-full bg-[--accent-primary] rounded-full transition-all duration-700 ease-out"
                    style={{ width: `${Math.min(100, progress)}%` }}
                  />
                </div>
              </div>
            )}
            {isFailed && sim.error_message && (
              <p className="text-xs text-[#f87171] line-clamp-2">{sim.error_message}</p>
            )}
          </div>
        )}

        <div className="mt-auto flex items-center gap-2 flex-wrap pt-1">
          {isCompleted && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => router.push(simHref)}
              icon={<ExternalLink size={13} />}
            >
              View report
            </Button>
          )}
          {userStopped && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => router.push(simHref)}
              icon={<ExternalLink size={13} />}
            >
              View run
            </Button>
          )}
          {isRunning && (
            <Button variant="secondary" size="sm" onClick={() => router.push(simHref)}>
              Watch live
            </Button>
          )}
          {isFailed && (
            <Button
              variant="secondary"
              size="sm"
              icon={<RotateCcw size={13} />}
              onClick={() => router.push("/new")}
            >
              New run
            </Button>
          )}

          {/* Controlled menu + delay before AlertDialog avoids Dropdown + Dialog dismiss layers stacking badly. */}
          <DropdownMenu modal={false} open={actionsMenuOpen} onOpenChange={setActionsMenuOpen}>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm" aria-label={`More actions for ${sim.business_name}`}>
                <MoreHorizontal size={15} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              className="w-48"
              onCloseAutoFocus={(e) => e.preventDefault()}
            >
              <DropdownMenuItem
                onSelect={() => {
                  setActionsMenuOpen(false);
                  router.push(simHref);
                }}
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Open
              </DropdownMenuItem>
              <DropdownMenuItem
                disabled={!MAY_STILL_BE_ACTIVE.has(sim.status)}
                onSelect={() => scheduleOpenAfterMenuCloses(setRevokeOpen)}
              >
                <Ban className="h-4 w-4 mr-2" />
                Revoke / stop run
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onSelect={() => scheduleOpenAfterMenuCloses(setDeleteOpen)}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <AlertDialog.Root
        open={deleteOpen}
        onOpenChange={(open) => {
          setDeleteOpen(open);
          if (!open) {
            setDeleting(false);
            if (dialogDelayTimerRef.current) {
              clearTimeout(dialogDelayTimerRef.current);
              dialogDelayTimerRef.current = null;
            }
          }
        }}
      >
        <AlertDialog.Portal>
          <AlertDialog.Overlay className="fixed inset-0 bg-black/60 z-[500] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:pointer-events-none" />
          <AlertDialog.Content className="fixed z-[500] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-[400px] mx-4 bg-[--bg-elevated] border border-[--border-default] rounded-[16px] p-6 shadow-2xl animate-scale-in data-[state=closed]:pointer-events-none">
            <AlertDialog.Title className="text-base font-medium text-[--text-primary] mb-2">
              Delete simulation?
            </AlertDialog.Title>
            <AlertDialog.Description className="text-sm text-[--text-secondary] mb-6">
              <strong className="text-[--text-primary]">{sim.business_name}</strong> and its report will be permanently
              removed. This cannot be undone.
            </AlertDialog.Description>
            <div className="flex justify-end gap-3">
              <AlertDialog.Cancel asChild>
                <Button variant="secondary" size="sm" type="button">
                  Cancel
                </Button>
              </AlertDialog.Cancel>
              <Button variant="danger" size="sm" type="button" loading={deleting} onClick={() => void confirmDelete()}>
                Delete
              </Button>
            </div>
          </AlertDialog.Content>
        </AlertDialog.Portal>
      </AlertDialog.Root>

      <AlertDialog.Root
        open={revokeOpen}
        onOpenChange={(open) => {
          setRevokeOpen(open);
          if (!open) {
            setRevoking(false);
            if (dialogDelayTimerRef.current) {
              clearTimeout(dialogDelayTimerRef.current);
              dialogDelayTimerRef.current = null;
            }
          }
        }}
      >
        <AlertDialog.Portal>
          <AlertDialog.Overlay className="fixed inset-0 bg-black/60 z-[500] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:pointer-events-none" />
          <AlertDialog.Content className="fixed z-[500] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-[400px] mx-4 bg-[--bg-elevated] border border-[--border-default] rounded-[16px] p-6 shadow-2xl animate-scale-in data-[state=closed]:pointer-events-none">
            <AlertDialog.Title className="text-base font-medium text-[--text-primary] mb-2">
              Stop this simulation?
            </AlertDialog.Title>
            <AlertDialog.Description className="text-sm text-[--text-secondary] mb-6">
              The run will stop and appear as Stopped in your list. You can delete it later.
            </AlertDialog.Description>
            <div className="flex justify-end gap-3">
              <AlertDialog.Cancel asChild>
                <Button variant="secondary" size="sm" type="button">
                  Cancel
                </Button>
              </AlertDialog.Cancel>
              <Button variant="primary" size="sm" type="button" loading={revoking} onClick={() => void confirmRevoke()}>
                Stop run
              </Button>
            </div>
          </AlertDialog.Content>
        </AlertDialog.Portal>
      </AlertDialog.Root>
    </>
  );
}
