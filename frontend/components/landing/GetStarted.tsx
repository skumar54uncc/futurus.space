import Link from "next/link";
import { Check, Zap, Shield, TrendingUp } from "lucide-react";
import { FreeTierLimitsNotice } from "@/components/landing/FreeTierLimitsNotice";
import { OPEN_ACCESS_AGENT_CAP, OPEN_ACCESS_TURN_CAP } from "@/lib/simulationLimits";

const features = [
  {
    icon: Zap,
    title: "Instant setup",
    body: "Sign in with email — no payment, no credit card. Your first simulation starts in under 60 seconds.",
  },
  {
    icon: TrendingUp,
    title: "Full simulation depth",
    body: `Up to ${OPEN_ACCESS_AGENT_CAP.toLocaleString("en-US")} AI agents over ${OPEN_ACCESS_TURN_CAP} turns per run. Not a toy demo.`,
  },
  {
    icon: Shield,
    title: "Actionable report",
    body: "Adoption curves, failure timeline, segment breakdown, risk matrix, and pivot suggestions in one export.",
  },
];

export function GetStarted() {
  return (
    <section id="get-started" className="py-24 relative scroll-mt-24">
      <div className="max-w-4xl mx-auto px-4">
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/[0.08] text-[11px] text-slate-300 uppercase tracking-widest mb-6">
            Get started
          </div>
          <h2 className="text-3xl sm:text-4xl font-serif italic text-white mb-4">
            Ready to see what happens next?
          </h2>
          <p className="text-slate-300 text-sm max-w-sm mx-auto leading-relaxed">
            Free to use. No payment. Run your first simulation in under a minute.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 items-start">
          {/* Feature list */}
          <div className="space-y-4">
            {features.map(({ icon: Icon, title, body }) => (
              <div key={title} className="flex gap-4 glass rounded-2xl p-5">
                <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0 mt-0.5">
                  <Icon className="w-4 h-4 text-indigo-400" />
                </div>
                <div>
                  <div className="text-sm font-medium text-white mb-1">{title}</div>
                  <p className="text-xs text-slate-300 leading-relaxed">{body}</p>
                </div>
              </div>
            ))}
          </div>

          {/* CTA card */}
          <div id="free-access" className="glass rounded-2xl p-8 scroll-mt-24" aria-label="Free access">
            <div className="mb-6">
              <div className="text-sm font-medium text-white mb-1">Free access</div>
              <div className="text-xs text-slate-300 leading-relaxed">
                No tiers, no paywalls. Limits exist while this project runs on personal API keys.
              </div>
            </div>

            <ul className="space-y-3 mb-8">
              {[
                "No payment required",
                `Up to ${OPEN_ACCESS_AGENT_CAP.toLocaleString("en-US")} agents per simulation`,
                "Full report on every completed run",
                "Email notification when done",
              ].map((item) => (
                <li key={item} className="flex items-center gap-2.5 text-sm text-slate-300">
                  <Check className="w-4 h-4 text-indigo-400 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>

            <Link
              href="/sign-up"
              className="block w-full text-center py-3.5 rounded-xl font-medium text-sm bg-indigo-600 hover:bg-indigo-500 text-white transition-all duration-150 shadow-[0_0_32px_rgba(99,102,241,0.3)] hover:shadow-[0_0_48px_rgba(99,102,241,0.45)]"
            >
              Create free account &rarr;
            </Link>

            <div className="mt-8">
              <FreeTierLimitsNotice />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
