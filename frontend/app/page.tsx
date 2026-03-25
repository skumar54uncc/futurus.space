import { Navbar } from "@/components/layout/Navbar";
import { Hero } from "@/components/landing/Hero";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { UseCases } from "@/components/landing/UseCases";
import { LivePreview } from "@/components/landing/LivePreview";
import { GetStarted } from "@/components/landing/GetStarted";
import { FAQ } from "@/components/landing/FAQ";
import { Footer } from "@/components/landing/Footer";

const MARQUEE_ITEMS = [
  "Startup validation",
  "Product pricing",
  "Story endings",
  "Policy impact",
  "Market entry",
  "Competitor response",
  "Viral loop modelling",
  "Course idea validation",
  "Local business planning",
  "Pricing elasticity",
  "App idea testing",
  "Audience research",
];

export default function LandingPage() {
  const loop = [...MARQUEE_ITEMS, ...MARQUEE_ITEMS];

  return (
    <main id="main-content" className="bg-void relative z-[1]">
      <Navbar />
      <Hero />
      <div
        className="w-full overflow-hidden py-3"
        style={{
          background: "var(--bg-surface)",
          borderTop: "1px solid var(--border-subtle)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
        aria-hidden="true"
      >
        <div className="flex gap-8 animate-marquee whitespace-nowrap w-max">
          {loop.map((item, i) => (
            <span key={`${item}-${i}`} className="mono text-xs text-[--text-tertiary] uppercase tracking-widest">
              {item} <span className="mx-2 opacity-40">·</span>
            </span>
          ))}
        </div>
      </div>
      <HowItWorks />
      <UseCases />
      <LivePreview />
      <GetStarted />
      <FAQ />
      <Footer />
    </main>
  );
}
