"use client";
import { UserButton } from "@clerk/nextjs";
import { Logo } from "@/components/ui/Logo";

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/5 bg-[hsl(234,60%,2%)]/90 backdrop-blur-xl">
      <div className="flex h-14 items-center justify-between px-4 md:px-6">
        <div className="md:hidden">
          <Logo size="sm" />
        </div>
        <div className="hidden md:block" />
        <div className="flex items-center gap-4 md:hidden">
          <UserButton afterSignOutUrl="/" />
        </div>
      </div>
    </header>
  );
}
