"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton, useUser } from "@clerk/nextjs";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Plus,
  Settings,
  Home,
  Mail,
  Zap,
  Lightbulb,
} from "lucide-react";
import { Logo } from "@/components/ui/Logo";
import { Tooltip } from "@/components/ui/Tooltip";
import { api } from "@/lib/api";
import type { UserProfile } from "@/lib/types";

const navigation = [
  { name: "Home", href: "/", icon: Home, external: true },
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "New simulation", href: "/new", icon: Plus },
  { name: "Ideas", href: "/ideas", icon: Lightbulb },
  { name: "Settings", href: "/settings", icon: Settings },
  { name: "Contact", href: "/contact", icon: Mail, external: true },
];

function getResetLabel(billingStart: string): string {
  const resetAt = new Date(new Date(billingStart).getTime() + 24 * 60 * 60 * 1000);
  const now = new Date();
  const diffMs = resetAt.getTime() - now.getTime();
  if (diffMs <= 0) return "Resets now";
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const mins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
  if (hours > 0) return `Resets in ${hours}h ${mins}m`;
  return `Resets in ${mins}m`;
}

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useUser();
  const [profile, setProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadProfile = async () => {
      try {
        const { data } = await api.get<UserProfile>("/api/auth/me");
        if (!cancelled) setProfile(data);
      } catch {
        // Ignore transient auth/network errors; the widget will retry on the next tick.
      }
    };

    void loadProfile();
    const interval = window.setInterval(() => {
      void loadProfile();
    }, 60_000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const remaining =
    profile && profile.daily_limit !== -1
      ? Math.max(0, profile.daily_limit - profile.simulations_this_month)
      : null;
  const exhausted = remaining !== null && remaining <= 0;

  const freeApiLimitNote =
    profile && remaining !== null ? (
      <span className="block mt-1.5 pt-1.5 border-t border-white/10 text-[11px] font-normal text-slate-300 leading-snug">
        Since I&apos;m using free LLM API keys for this project, I have to limit usage — your plan allows{" "}
        {profile.daily_limit} simulation{profile.daily_limit !== 1 ? "s" : ""} per day.
      </span>
    ) : null;

  return (
    <aside className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0">
      <div className="flex flex-col flex-grow border-r border-[hsl(234,25%,14%)] bg-[hsl(234,33%,8%)] pt-5 overflow-y-auto">
        <div className="flex items-center flex-shrink-0 px-5">
          <Link href="/dashboard" aria-label="Dashboard home">
            <Logo size="md" />
          </Link>
        </div>
        <div className="mt-8 flex-grow flex flex-col">
          <nav className="flex-1 px-3 space-y-1" aria-label="Dashboard">
            {navigation.map((item) => {
              const isActive =
                !item.external &&
                (pathname === item.href ||
                  pathname.startsWith(item.href + "/"));
              const LinkComp = item.external ? "a" : Link;
              const extraProps = item.external
                ? { target: undefined, rel: undefined }
                : {};
              return (
                <LinkComp
                  key={item.name}
                  href={item.href}
                  {...extraProps}
                  className={cn(
                    "group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all",
                    isActive
                      ? "bg-indigo-500/10 text-indigo-400 border-l-2 border-indigo-500"
                      : "text-slate-500 hover:bg-white/5 hover:text-slate-300"
                  )}
                >
                  <item.icon
                    className={cn(
                      "mr-3 h-4.5 w-4.5 flex-shrink-0",
                      isActive ? "text-indigo-400" : "text-slate-600"
                    )}
                  />
                  {item.name}
                </LinkComp>
              );
            })}
          </nav>
        </div>

        {/* Credits / daily limit widget */}
        {profile && remaining !== null && (
          <div className="mx-3 mb-3">
            <Tooltip
              content={
                exhausted ? (
                  <>
                    <span className="block">
                      Daily limit reached. {getResetLabel(profile.billing_period_start)}.
                    </span>
                    {freeApiLimitNote}
                  </>
                ) : (
                  <>
                    <span className="block">
                      {remaining} of {profile.daily_limit} simulation(s) left today.{" "}
                      {getResetLabel(profile.billing_period_start)}.
                    </span>
                    {freeApiLimitNote}
                  </>
                )
              }
              side="right"
            >
              <div
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2.5 rounded-lg border transition-colors cursor-default",
                  exhausted
                    ? "border-amber-500/30 bg-amber-500/5"
                    : "border-[--border-subtle] bg-white/[0.02]"
                )}
              >
                <Zap
                  size={15}
                  className={cn(
                    exhausted ? "text-amber-400" : "text-indigo-400"
                  )}
                />
                <div className="flex-1 min-w-0">
                  <p
                    className={cn(
                      "text-xs font-medium",
                      exhausted ? "text-amber-300" : "text-[--text-primary]"
                    )}
                  >
                    {exhausted
                      ? "No credits left"
                      : `${remaining} credit${remaining !== 1 ? "s" : ""} left`}
                  </p>
                  <p className="text-[10px] text-[--text-tertiary] mt-0.5">
                    {exhausted
                      ? getResetLabel(profile.billing_period_start)
                      : `${profile.daily_limit}/day \u00B7 Free tier`}
                  </p>
                </div>
              </div>
            </Tooltip>
          </div>
        )}

        <div className="flex-shrink-0 border-t border-white/5 p-4 mt-auto">
          <div className="flex items-center gap-3 px-1">
            <UserButton afterSignOutUrl="/" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[--text-primary] truncate">
                {user?.fullName || "Account"}
              </p>
              <p className="text-xs text-[--text-tertiary] truncate">
                {user?.primaryEmailAddress?.emailAddress || ""}
              </p>
            </div>
          </div>
          <p className="text-xs text-slate-400 mt-3 px-1">Powered by MiroFish</p>
        </div>
      </div>
    </aside>
  );
}
