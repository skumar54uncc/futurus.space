"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ClerkLoaded,
  ClerkLoading,
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
} from "@clerk/nextjs";
import { Logo } from "@/components/ui/Logo";
import { Button } from "@/components/ui/button";

/** Module-level: same order on server and client (keys use href, not labels). */
const LANDING_NAV_LINKS = [
  ["How it works", "#how-it-works"],
  ["Pricing", "#pricing"],
  ["Get started", "#get-started"],
  ["FAQ", "#faq"],
] as const;

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  /** Defer anchor labels until mount so SSR + first client paint match (fixes Clerk/HMR text drift). */
  const [navLinksReady, setNavLinksReady] = useState(false);

  useEffect(() => {
    setNavLinksReady(true);
  }, []);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 40);
    fn();
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-[200] transition-all duration-300 ${
        scrolled
          ? "border-b border-[--border-default] bg-[rgba(1,1,9,0.85)] backdrop-blur-xl"
          : "bg-transparent"
      }`}
      aria-label="Primary"
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" aria-label="Futurus home">
          <Logo />
        </Link>

        <div
          className="hidden md:flex items-center gap-6 min-h-5 min-w-[16rem]"
          suppressHydrationWarning
        >
          {navLinksReady
            ? LANDING_NAV_LINKS.map(([label, href]) => (
                <a
                  key={href}
                  href={href}
                  className="text-sm text-[--text-secondary] hover:text-[--text-primary] transition-colors"
                >
                  {label}
                </a>
              ))
            : null}
        </div>

        <div className="flex items-center gap-3 min-h-9" suppressHydrationWarning>
          <ClerkLoading>
            <div className="flex items-center gap-2" aria-hidden>
              <div className="h-8 w-[4.5rem] rounded-md bg-white/[0.06]" />
              <div className="h-8 w-[5.25rem] rounded-md bg-white/[0.06]" />
            </div>
          </ClerkLoading>
          <ClerkLoaded>
            <SignedOut>
              <SignInButton mode="modal">
                <Button variant="ghost" size="sm">
                  Sign in
                </Button>
              </SignInButton>
              <SignUpButton mode="modal">
                <Button variant="primary" size="sm">
                  Start free
                </Button>
              </SignUpButton>
            </SignedOut>
            <SignedIn>
              <Button variant="secondary" size="sm" asChild>
                <Link href="/dashboard">Dashboard</Link>
              </Button>
              <UserButton afterSignOutUrl="/" />
            </SignedIn>
          </ClerkLoaded>
        </div>
      </div>
    </nav>
  );
}
