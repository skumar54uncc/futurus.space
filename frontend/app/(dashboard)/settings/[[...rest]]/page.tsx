"use client";

import { UserProfile } from "@clerk/nextjs";
import { PageShell } from "@/components/layout/PageShell";
import { futurusClerkTheme, getClerkLogoUrlForClient } from "@/lib/clerk-appearance";
import { Shield, Sparkles, KeyRound, Mail } from "lucide-react";

/**
 * Clerk requires a catch-all segment for `<UserProfile routing="path" />` so in-app
 * sub-routes like `/settings/security` resolve correctly.
 * @see https://clerk.com/docs/components/user/user-profile
 */
export default function SettingsPage() {
  return (
    <PageShell
      wide
      title="Settings"
      description="Manage your profile, emails, passwords, and connected accounts. Changes sync everywhere you use this Clerk account."
      actions={
        <span className="inline-flex items-center gap-2 rounded-full border border-[--border-subtle] bg-[--bg-surface]/80 px-3 py-1.5 text-xs text-[--text-secondary]">
          <Shield className="h-3.5 w-3.5 text-[--text-accent] shrink-0" aria-hidden />
          Secured with Clerk
        </span>
      }
    >
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-[--border-subtle] bg-[--bg-surface] p-4 flex gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[--accent-primary-muted] border border-[--border-accent]">
              <Sparkles className="h-5 w-5 text-[--text-accent]" aria-hidden />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-[--text-primary]">Account on Futurus</p>
              <p className="text-xs text-[--text-tertiary] mt-0.5 leading-relaxed">
                This panel is your single place to update how you sign in and what others see.
              </p>
            </div>
          </div>
          <div className="rounded-2xl border border-[--border-subtle] bg-[--bg-surface] p-4 flex gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[--bg-elevated] border border-[--border-default]">
              <Mail className="h-5 w-5 text-[--text-secondary]" aria-hidden />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-[--text-primary]">Email &amp; profile</p>
              <p className="text-xs text-[--text-tertiary] mt-0.5 leading-relaxed">
                Add backup emails, update your name, and manage your avatar from the Profile tab.
              </p>
            </div>
          </div>
          <div className="rounded-2xl border border-[--border-subtle] bg-[--bg-surface] p-4 flex gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[--bg-elevated] border border-[--border-default]">
              <KeyRound className="h-5 w-5 text-[--text-secondary]" aria-hidden />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-[--text-primary]">Security</p>
              <p className="text-xs text-[--text-tertiary] mt-0.5 leading-relaxed">
                Passwords, 2FA, sessions, and connected OAuth providers live under Security.
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-[--border-default] bg-[--bg-deep] shadow-[0_12px_40px_rgba(0,0,0,0.12)] overflow-hidden">
          <UserProfile
            path="/settings"
            routing="path"
            appearance={{
              ...futurusClerkTheme,
              layout: {
                logoImageUrl:
                  getClerkLogoUrlForClient() ?? "https://futurus.dev/brand/futurus-logo-dark.svg",
              },
              elements: {
                rootBox: "w-full max-w-full",
                scrollBox: "w-full max-w-full p-0",
                card: "bg-transparent shadow-none border-0 w-full max-w-full rounded-none",
                navbar: "bg-[hsl(234,28%,9%)] border-b border-[--border-subtle] px-4 py-3",
                navbarButton: "text-[--text-secondary] data-[active=true]:text-[--text-primary]",
                navbarMobileMenuButton: "text-[--text-primary]",
                formButtonPrimary: "bg-indigo-600 hover:bg-indigo-500",
                formFieldInput:
                  "bg-[hsl(234,28%,11%)] border-[--border-default] text-[--text-primary] placeholder:text-[--text-tertiary]",
                profileSectionTitle: "text-[--text-primary]",
                profileSectionContent: "text-[--text-secondary]",
                identityPreviewText: "truncate max-w-[min(100%,280px)] sm:max-w-none",
                badge: "border-[--border-subtle]",
              },
            }}
          />
        </div>
      </div>
    </PageShell>
  );
}
