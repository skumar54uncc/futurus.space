"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ClerkLoaded,
  ClerkLoading,
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
} from "@clerk/nextjs";
import { Menu, X } from "lucide-react";
import { Logo } from "@/components/ui/Logo";
import { Button } from "@/components/ui/button";

/** Module-level: same order on server and client (keys use href, not labels). */
const LANDING_NAV_LINKS = [
  ["How it works", "/#how-it-works"],
  ["Free access", "/#free-access"],
  ["Ideas", "/ideas"],
  ["Get started", "/#get-started"],
  ["FAQ", "/#faq"],
] as const;

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  /** Defer anchor labels until mount so SSR + first client paint match (fixes Clerk/HMR text drift). */
  const [navLinksReady, setNavLinksReady] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinkNodes = useMemo(
    () =>
      navLinksReady
        ? LANDING_NAV_LINKS.map(([label, href]) =>
            !href.includes("#") ? (
              <Link
                key={href}
                href={href}
                onClick={() => setMobileMenuOpen(false)}
                className="text-sm text-[--text-secondary] hover:text-[--text-primary] transition-colors"
              >
                {label}
              </Link>
            ) : (
              <a
                key={href}
                href={href}
                onClick={() => setMobileMenuOpen(false)}
                className="text-sm text-[--text-secondary] hover:text-[--text-primary] transition-colors"
              >
                {label}
              </a>
            )
          )
        : null,
    [navLinksReady]
  );

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

        <div className="hidden md:flex items-center gap-6 min-h-5 min-w-[16rem]" suppressHydrationWarning>
          {navLinkNodes}
        </div>

        <div className="hidden md:flex items-center gap-3 min-h-9" suppressHydrationWarning>
          <ClerkLoading>
            <div className="flex items-center gap-2" aria-hidden>
              <div className="h-8 w-[4.5rem] rounded-md bg-white/[0.06]" />
              <div className="h-8 w-[5.25rem] rounded-md bg-white/[0.06]" />
            </div>
          </ClerkLoading>
          <ClerkLoaded>
            <SignedOut>
              <SignInButton mode="modal">
                <Button variant="ghost" size="sm" aria-label="Sign in to Futurus">
                  Sign in
                </Button>
              </SignInButton>
              <SignUpButton mode="modal">
                <Button variant="primary" size="sm" aria-label="Start for free">
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

        <button
          type="button"
          className="md:hidden inline-flex items-center justify-center h-10 w-10 rounded-[10px] border border-[--border-default] bg-[--bg-surface] text-[--text-primary] hover:border-[--border-strong] transition-colors"
          aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-nav-panel"
          onClick={() => setMobileMenuOpen((open) => !open)}
        >
          {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      <div
        id="mobile-nav-panel"
        className={`md:hidden border-t border-[--border-subtle] bg-[rgba(1,1,9,0.96)] backdrop-blur-xl overflow-hidden transition-all duration-300 ${
          mobileMenuOpen ? "max-h-[26rem] opacity-100" : "max-h-0 opacity-0"
        }`}
        aria-hidden={!mobileMenuOpen}
      >
        <div className="max-w-6xl mx-auto px-6 py-4 space-y-4">
          <div className="grid gap-2">
            {navLinkNodes}
          </div>

          <div className="flex flex-col gap-2 pt-2 border-t border-[--border-subtle]">
            <ClerkLoaded>
              <SignedOut>
                <SignInButton mode="modal">
                  <Button variant="ghost" size="sm" className="w-full justify-center" aria-label="Sign in to Futurus">
                    Sign in
                  </Button>
                </SignInButton>
                <SignUpButton mode="modal">
                  <Button variant="primary" size="sm" className="w-full justify-center" aria-label="Start for free">
                    Start free
                  </Button>
                </SignUpButton>
              </SignedOut>
              <SignedIn>
                <Button variant="secondary" size="sm" asChild className="w-full justify-center">
                  <Link href="/dashboard">Dashboard</Link>
                </Button>
              </SignedIn>
            </ClerkLoaded>
          </div>
        </div>
      </div>
    </nav>
  );
}
