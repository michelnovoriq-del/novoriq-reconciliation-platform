import Link from "next/link";
import { Sparkles } from "lucide-react";

export function AuthCard({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}) {
  return (
    <main className="grid min-h-screen bg-cream lg:grid-cols-[1fr_0.9fr]">
      <section className="relative hidden overflow-hidden bg-skybrand p-10 text-white lg:block">
        <div className="absolute -right-20 top-24 h-72 w-72 rounded-full bg-white/20 blur-3xl" />
        <div className="absolute bottom-16 left-20 h-44 w-44 rounded-full bg-violet-300/30 blur-3xl" />
        <Link href="/" className="relative z-10 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-deepblue">
            <Sparkles className="h-5 w-5" />
          </span>
          <span className="text-lg font-black">Novoriq</span>
        </Link>
        <div className="relative z-10 mt-32 max-w-xl">
          <p className="mb-4 text-sm font-bold uppercase tracking-[0.2em] text-sky-100">Controlled reconciliation</p>
          <h1 className="text-5xl font-black leading-tight tracking-tight">
            Financial file operations with clarity at every step.
          </h1>
          <p className="mt-6 text-lg leading-8 text-sky-50">
            Upload CSVs, map columns, normalize records, and prepare reconciliation runs in a focused workspace.
          </p>
        </div>
      </section>
      <section className="flex items-center justify-center p-5">
        <div className="w-full max-w-md rounded-3xl border border-white/70 bg-white/85 p-7 shadow-soft backdrop-blur">
          <div className="mb-7">
            <Link href="/" className="mb-8 inline-flex items-center gap-2 text-sm font-black text-deepblue lg:hidden">
              <Sparkles className="h-4 w-4" />
              Novoriq
            </Link>
            <h1 className="text-3xl font-black tracking-tight text-ink">{title}</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
          </div>
          {children}
          <div className="mt-6 text-center text-sm text-slate-600">{footer}</div>
        </div>
      </section>
    </main>
  );
}
