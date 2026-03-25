import Link from "next/link";
import { Check } from "lucide-react";
import { FreeTierLimitsNotice } from "@/components/landing/FreeTierLimitsNotice";
import { OPEN_ACCESS_AGENT_CAP, OPEN_ACCESS_TURN_CAP } from "@/lib/simulationLimits";

const highlights = [
  "Sign up with email — no payment",
  `Run full simulations with up to ${OPEN_ACCESS_AGENT_CAP.toLocaleString("en-US")} AI agents and ${OPEN_ACCESS_TURN_CAP} turns`,
  "Adoption curves, risks, and pivot ideas in one report",
];

export function GetStarted() {
  return (
    <section id="get-started" className="py-24 relative scroll-mt-24">
      <div className="max-w-3xl mx-auto px-4 text-center">
        <h2 className="text-h2 font-medium text-[--text-primary] mb-4">
          Ready to see what happens next?
        </h2>
        <p className="text-[--text-tertiary] mb-10 text-sm leading-relaxed">
          Futurus is free to use: sign in and run simulations. No payment, no tiers — just usage limits
          while the project runs on personal API keys.
        </p>

        <div className="glass rounded-2xl p-10 text-left max-w-xl mx-auto">
          <ul className="space-y-4 mb-10">
            {highlights.map((item) => (
              <li key={item} className="flex items-start gap-3 text-sm text-slate-400">
                <Check className="w-5 h-5 text-indigo-400 mt-0.5 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
          <Link
            href="/sign-up"
            className="block w-full text-center py-3.5 rounded-lg font-medium text-sm bg-indigo-600 hover:bg-indigo-500 text-white transition-colors animate-pulse-glow"
          >
            Create an account &rarr;
          </Link>

          <div id="pricing" className="mt-8 scroll-mt-24">
            <FreeTierLimitsNotice />
          </div>
        </div>
      </div>
    </section>
  );
}
