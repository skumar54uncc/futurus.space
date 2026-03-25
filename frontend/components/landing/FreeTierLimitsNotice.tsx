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
          : "border border-white/10 bg-white/[0.02] text-slate-500",
        className
      )}
    >
      <p className="mb-2">
        <span className={isLight ? "text-green-900 font-medium" : "text-slate-400"}>Personal project.</span>{" "}
        Right now Futurus runs on free API keys.         Each simulation is limited to {OPEN_ACCESS_AGENT_CAP.toLocaleString("en-US")} AI agents and {OPEN_ACCESS_TURN_CAP}{" "}
        turns so anyone can try it without paying. If I could pay for servers and stronger AI access, the same setup could grow to about{" "}
        {`${FULL_SCALE_AGENT_CAP.toLocaleString("en-US")}+`} agents and {`${FULL_SCALE_TURN_CAP}+`} turns—that&apos;s where I hope to take it.
      </p>
      <p className="mb-2">
        I&apos;m in the U.S. on an F-1 visa and I&apos;m looking for work. I can&apos;t charge users or turn this into income that would pay for costly API
        keys—that&apos;s why you see these limits. It&apos;s not because I don&apos;t want to go bigger.
      </p>
      <p>
        Clearer, deeper results would also need paid access to smarter models (for example{" "}
        <span className={isLight ? "text-green-950" : "text-slate-400"}>OpenAI</span> or{" "}
        <span className={isLight ? "text-green-950" : "text-slate-400"}>Anthropic</span> Claude)—not just another free key.
      </p>
    </div>
  );
}
