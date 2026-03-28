import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { LayoutDashboard, Plus, Settings, Home, Mail } from "lucide-react";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

const mobileNav: Array<{
  href: string;
  icon: LucideIcon;
  label: string;
  primary?: boolean;
}> = [
  { href: "/", icon: Home, label: "Home" },
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/new", icon: Plus, label: "New", primary: true },
  { href: "/settings", icon: Settings, label: "Settings" },
  { href: "/contact", icon: Mail, label: "Contact" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh bg-void">
      <Sidebar />
      <div className="md:pl-64 flex flex-col min-h-dvh pb-20 md:pb-0">
        <Header />
        <main id="main-content" className="flex-1">
          {children}
        </main>
      </div>

      <nav
        className="fixed bottom-0 left-0 right-0 md:hidden z-[200] bg-[rgba(5,5,15,0.92)] backdrop-blur-xl border-t border-[--border-subtle] pb-[env(safe-area-inset-bottom)]"
        aria-label="Mobile navigation"
      >
        <div className="flex items-center justify-around h-16 px-2">
          {mobileNav.map(({ href, icon: Icon, label, primary }) => (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center gap-1 flex-1 py-2 rounded-[10px] transition-colors min-h-[44px] justify-center ${
                primary ? "text-[--accent-primary]" : "text-[--text-tertiary] hover:text-[--text-secondary]"
              }`}
              aria-label={label}
            >
              <Icon size={22} />
              <span className="text-[10px]">{label}</span>
            </Link>
          ))}
        </div>
      </nav>
    </div>
  );
}
