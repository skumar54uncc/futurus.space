import type { Metadata } from "next";
import Link from "next/link";
import { Logo } from "@/components/ui/Logo";
import { ContactForm } from "@/components/contact/ContactForm";

export const metadata: Metadata = {
  title: "Contact — Futurus",
  description: "Reach the person behind Futurus — questions, ideas, or feedback welcome.",
};

export default function ContactPage() {
  return (
    <div className="min-h-dvh bg-void text-slate-300" id="main-content">
      <header className="border-b border-white/5 px-4 py-6">
        <div className="max-w-3xl mx-auto flex items-center justify-between gap-4">
          <Link
            href="/"
            className="flex items-center gap-3 text-slate-400 hover:text-white transition-colors duration-150"
          >
            <Logo size="sm" />
            <span className="text-sm">Home</span>
          </Link>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-serif italic text-white mb-3">Say hello</h1>
        <p className="text-slate-400 text-[15px] leading-relaxed max-w-xl mb-2">
          Futurus is a solo, curiosity-driven project. If something&apos;s unclear, you&apos;ve hit a bug, or you just
          want to talk through an idea — write me. I read every message and I&apos;m happy to help.
        </p>
        <p className="text-slate-300 text-sm max-w-xl mb-8">
          No pressure, no sales pitch — just a direct line to the person who built this.
        </p>
        <ContactForm />
        <p className="text-xs text-slate-400 mt-10 max-w-lg">
          How we handle what you send: see our{" "}
          <Link href="/privacy" className="text-indigo-400/90 hover:text-indigo-300 underline underline-offset-2">
            Privacy policy
          </Link>
          .
        </p>
      </main>
    </div>
  );
}
