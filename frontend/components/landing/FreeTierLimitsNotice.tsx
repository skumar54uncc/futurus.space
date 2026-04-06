import { cn } from "@/lib/utils";
import {
  FULL_SCALE_AGENT_CAP,
  FULL_SCALE_TURN_CAP,
  OPEN_ACCESS_AGENT_CAP,
  OPEN_ACCESS_TURN_CAP,
} from "@/lib/simulationLimits";

type Props = {
  className?: string;
  /** `light` for pale panels (e.g. wizard); default matches the dark landing page. */
  variant?: "dark" | "light";
};

export function FreeTierLimitsNotice({ className, variant = "dark" }: Props) {
  const isLight = variant === "light";

  return (
    <div
      className={cn(
        "rounded-lg px-4 py-3 text-left text-xs leading-relaxed",
        isLight
          ? "border border-green-200 bg-white/80 text-green-900/80"
          : "border border-white/10 bg-white/[0.02] text-slate-300",
        className
      )}
    >
      <p>
        <span className={isLight ? "text-green-900 font-medium" : "text-slate-200"}>Personal project.</span>{" "}
        Right now Futurus runs on free API keys, so simulations are capped at {OPEN_ACCESS_AGENT_CAP.toLocaleString("en-US")} agents and {OPEN_ACCESS_TURN_CAP} turns.
        If I can fund stronger infrastructure later, those limits can grow toward {`${FULL_SCALE_AGENT_CAP.toLocaleString("en-US")}+`} agents and {`${FULL_SCALE_TURN_CAP}+`} turns.
      </p>
    </div>
  );
}
