import type { ReactNode } from "react";
import Link from "next/link";
import { Logo } from "@/components/ui/Logo";

export function LegalPageShell({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-dvh bg-void text-slate-300" id="main-content">
      <header className="border-b border-white/5 px-4 py-6">
        <div className="max-w-3xl mx-auto flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-3 text-slate-400 hover:text-white transition-colors duration-150">
            <Logo size="sm" />
            <span className="text-sm">Home</span>
          </Link>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-4 py-12">
        <h1 className="text-h2 font-medium text-[--text-primary] mb-2">{title}</h1>
        <p className="text-xs text-slate-600 mb-10">
          Last updated: {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
        </p>
        <div className="max-w-none space-y-5 text-slate-400 text-[15px] leading-relaxed [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-white [&_h2]:mt-10 [&_h2]:mb-1 [&_h2]:first:mt-0 [&_p]:mt-0 [&_ul]:mt-2 [&_ul]:list-disc [&_ul]:pl-5 [&_li]:mt-1.5 [&_strong]:text-slate-300">
          {children}
        </div>
      </main>
    </div>
  );
}
