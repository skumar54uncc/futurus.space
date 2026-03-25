"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton, useUser } from "@clerk/nextjs";
import { cn } from "@/lib/utils";
import { LayoutDashboard, Plus, Settings } from "lucide-react";
import { Logo } from "@/components/ui/Logo";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "New simulation", href: "/new", icon: Plus },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useUser();

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
              const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.name}
                  href={item.href}
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
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex-shrink-0 border-t border-white/5 p-4 mt-auto">
          <div className="flex items-center gap-3 px-1">
            <UserButton afterSignOutUrl="/" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[--text-primary] truncate">{user?.fullName || "Account"}</p>
              <p className="text-xs text-[--text-tertiary] truncate">
                {user?.primaryEmailAddress?.emailAddress || ""}
              </p>
            </div>
          </div>
          <p className="text-xs text-slate-700 mt-3 px-1">Powered by MiroFish</p>
        </div>
      </div>
    </aside>
  );
}
