"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Files, Home, LogOut, PlusCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/hooks/use-auth";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/files", label: "Files", icon: Files },
  { href: "/files/upload", label: "Upload", icon: PlusCircle },
  { href: "/reconciliation-runs", label: "Runs", icon: BarChart3 },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { logout, user } = useAuth();

  return (
    <div className="min-h-screen bg-cream cream-grid">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 border-r border-white/60 bg-white/80 p-5 shadow-soft backdrop-blur xl:block">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-skybrand text-white shadow-glass">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <p className="font-black tracking-tight text-ink">Novoriq</p>
            <p className="text-xs font-semibold text-slate-500">Reconciliation Agent</p>
          </div>
        </Link>

        <nav className="mt-10 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold transition",
                  active
                    ? "bg-skybrand text-white shadow-glass"
                    : "text-slate-600 hover:bg-sky-50 hover:text-deepblue",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-5 left-5 right-5 rounded-2xl border border-slate-200 bg-white p-4">
          <p className="truncate text-sm font-bold text-ink">{user?.full_name || user?.email}</p>
          <p className="truncate text-xs text-slate-500">{user?.email}</p>
          <Button className="mt-4 w-full" variant="outline" size="sm" onClick={logout}>
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </div>
      </aside>

      <header className="sticky top-0 z-10 border-b border-white/60 bg-white/80 px-4 py-3 backdrop-blur xl:hidden">
        <div className="flex items-center justify-between">
          <Link href="/dashboard" className="font-black text-ink">Novoriq</Link>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
        <nav className="mt-3 flex gap-2 overflow-x-auto pb-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex shrink-0 items-center gap-2 rounded-full px-3 py-2 text-xs font-bold",
                  active ? "bg-skybrand text-white" : "bg-white text-slate-600",
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>

      <main className="px-4 py-6 sm:px-6 xl:ml-72 xl:px-10 xl:py-10">{children}</main>
    </div>
  );
}
