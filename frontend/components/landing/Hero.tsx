"use client";
import Link from "next/link";
import { useEffect, useMemo, useRef } from "react";

function StarField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const stars = Array.from({ length: 200 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.2 + 0.3,
      speed: Math.random() * 0.3 + 0.05,
      opacity: Math.random() * 0.6 + 0.2,
      phase: Math.random() * Math.PI * 2,
    }));

    let frame: number;
    const draw = (t: number) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const s of stars) {
        const flicker = 0.5 + 0.5 * Math.sin(t * 0.001 * s.speed + s.phase);
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(165, 180, 252, ${s.opacity * flicker})`;
        ctx.fill();
      }
      frame = requestAnimationFrame(draw);
    };
    if (!reducedMotion) {
      frame = requestAnimationFrame(draw);
    }

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 z-0" aria-hidden="true" />;
}

export function Hero() {
  const stats = useMemo(
    () => [
      ["1,000", "AI agents per run"],
      ["40", "simulation turns"],
      ["6", "report sections"],
      ["16", "ideas published"],
    ],
    []
  );

  return (
    <section id="hero" aria-label="Hero" className="relative min-h-dvh flex items-center justify-center overflow-hidden pt-24">
      <StarField />

      {/* Concentric rings */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute inset-0 flex items-center justify-center">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="absolute rounded-full border border-indigo-500/10 animate-ring"
              style={{
                width: `${200 + i * 200}px`,
                height: `${200 + i * 200}px`,
                animationDelay: `${i * 1.3}s`,
              }}
            />
          ))}
        </div>
      </div>

      {/* Radial gradient glow behind text */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-500/5 rounded-full blur-[120px]" />
      </div>

      <div className="relative z-10 text-center max-w-3xl mx-auto px-4">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-xs text-indigo-300 mb-8">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          Powered by multi-agent AI simulation
        </div>

        <h1
          aria-label="See what is about to be."
          className="text-5xl sm:text-6xl lg:text-7xl leading-[1.1] tracking-tight mb-6"
        >
          <span className="font-serif italic text-white">See what is</span>
          <br />
          <span className="font-light text-slate-300">about to be.</span>
        </h1>

        <p className="text-lg text-slate-300 max-w-lg mx-auto mb-10 leading-relaxed">
          Write any idea in plain English. Futurus stress-tests it through up to 1,000 AI minds —
          and shows you exactly what will happen before you commit.
        </p>

        <div className="flex items-center justify-center gap-4 mb-12 flex-wrap">
          <Link
            href="/sign-up"
            className="px-8 py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium transition-all duration-150 ease-out active:scale-[0.98] shadow-[0_0_32px_rgba(99,102,241,0.35)] hover:shadow-[0_0_48px_rgba(99,102,241,0.5)]"
          >
            Simulate your idea &rarr;
          </Link>
          <a
            href="#how-it-works"
            className="px-8 py-3.5 rounded-xl font-medium text-slate-300 border border-white/15 hover:border-indigo-500/40 hover:text-white hover:bg-indigo-500/5 transition-all duration-150 ease-out active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-[--bg-void]"
          >
            See how it works
          </a>
        </div>

        {/* Social-proof stat strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-0 md:divide-x md:divide-white/10 max-w-3xl mx-auto">
          {stats.map(([num, label]) => (
            <div key={label} className="text-center md:px-4">
              <div className="text-3xl sm:text-4xl font-semibold tracking-tight bg-gradient-to-r from-indigo-200 via-indigo-400 to-violet-400 bg-clip-text text-transparent">
                {num}
              </div>
              <div className="text-[11px] text-slate-400 uppercase tracking-widest mt-1">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
