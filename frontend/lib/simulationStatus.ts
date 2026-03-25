import type { Simulation } from "@/lib/types";

export function simulationUiFromStatus(sim: Simulation): { progress: number; message: string } {
  const maxT = Math.max(1, sim.max_turns || 1);
  const turn = sim.current_turn ?? 0;
  const agents = sim.agents_active ?? 0;

  switch (sim.status) {
    case "queued":
      // Avoid a fake "3%" that looks like a stuck progress bar; UI shows indeterminate until status advances.
      return { progress: 0, message: "Queued — starting soon…" };
    case "building_seed":
      return { progress: 10, message: "Building market context from your inputs…" };
    case "generating_personas":
      return { progress: 18, message: "Creating AI customer agents…" };
    case "running":
      return {
        progress: 25 + Math.min(58, Math.round((turn / maxT) * 58)),
        message:
          agents > 0
            ? `Running simulation — turn ${turn} of ${maxT} · ${agents.toLocaleString()} agents active`
            : `Running simulation — turn ${turn} of ${maxT}`,
      };
    case "generating_report":
      return { progress: 92, message: "Simulation complete — writing your report…" };
    case "completed":
      return { progress: 100, message: "Done — opening your report…" };
    case "failed":
      return {
        progress: -1,
        message: sim.error_message?.trim() || "Simulation failed. You can try again from a new run.",
      };
    case "revoked":
      return { progress: 0, message: "This run was stopped." };
    default:
      return { progress: 5, message: "Working…" };
  }
}
