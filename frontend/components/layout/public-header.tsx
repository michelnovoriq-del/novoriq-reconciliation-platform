"use client";
import Link from "next/link";
import { useState } from "react";
import { Menu, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const links = [["Features", "/features"], ["How It Works", "/how-it-works"], ["Pricing", "/pricing"], ["Security", "/security"], ["Support", "/support"]] as const;
export function PublicHeader() {
  const [open, setOpen] = useState(false);
  return <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 backdrop-blur">
    <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
      <Link href="/" className="flex items-center gap-2 font-black text-ink"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-skybrand text-white"><Sparkles className="h-4 w-4" /></span>Novoriq</Link>
      <nav aria-label="Primary navigation" className="hidden items-center gap-6 lg:flex">{links.map(([label, href]) => <Link key={href} href={href} className="text-sm font-bold text-slate-600 hover:text-deepblue">{label}</Link>)}<details className="relative"><summary className="cursor-pointer list-none text-sm font-bold text-slate-600 hover:text-deepblue">Use Cases</summary><div className="absolute right-0 mt-3 w-56 rounded-xl border bg-white p-2 shadow-soft">{[["Bookkeepers", "/use-cases/bookkeepers"], ["Accounting Firms", "/use-cases/accounting-firms"], ["Ecommerce", "/use-cases/ecommerce-reconciliation"]].map(([l,h]) => <Link key={h} href={h} className="block rounded-lg px-3 py-2 text-sm font-semibold hover:bg-sky-50">{l}</Link>)}</div></details></nav>
      <div className="hidden gap-2 sm:flex"><Button asChild variant="ghost" size="sm"><Link href="/login">Login</Link></Button><Button asChild variant="sky" size="sm"><Link href="/register">Start Free</Link></Button></div>
      <button className="rounded-lg p-2 lg:hidden" aria-label="Toggle navigation" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
    </div>{open ? <nav aria-label="Mobile navigation" className="border-t bg-white px-5 py-4 lg:hidden">{links.map(([label, href]) => <Link onClick={() => setOpen(false)} key={href} href={href} className="block py-2 font-bold">{label}</Link>)}<Link href="/use-cases/bookkeepers" className="block py-2 font-bold">Use Cases</Link><div className="mt-3 flex gap-2"><Button asChild variant="outline"><Link href="/login">Login</Link></Button><Button asChild variant="sky"><Link href="/register">Start Free</Link></Button></div></nav> : null}
  </header>;
}
