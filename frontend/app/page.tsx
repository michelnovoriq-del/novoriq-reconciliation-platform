"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, CheckCircle2, FileUp, GitBranch, Layers3, ScanSearch, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const steps = [
  { title: "Drop files", description: "Upload clean CSV inputs into a controlled workspace.", icon: FileUp, tone: "bg-sky-100 text-deepblue" },
  { title: "Map columns", description: "Align source columns to Novoriq standard fields.", icon: GitBranch, tone: "bg-violet-100 text-violet-700" },
  { title: "Normalize records", description: "Convert rows into comparable financial records.", icon: Layers3, tone: "bg-green-100 text-green-700" },
  { title: "Review reconciliation runs", description: "Create runs that prepare files for matching.", icon: ScanSearch, tone: "bg-amber-100 text-amber-700" },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-cream text-ink">
      <section className="relative min-h-[92vh] overflow-hidden bg-skybrand text-white">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(255,255,255,0.30),transparent_28%),radial-gradient(circle_at_80%_30%,rgba(167,139,250,0.35),transparent_26%),linear-gradient(135deg,#0EA5E9,#0284C7)]" />
        <motion.div
          className="absolute left-[12%] top-32 h-28 w-28 rounded-3xl border border-white/25 bg-white/10 backdrop-blur"
          animate={{ y: [0, -18, 0], rotate: [0, 4, 0] }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute bottom-24 right-[12%] h-36 w-36 rounded-full bg-amber-300/25 blur-sm"
          animate={{ y: [0, 22, 0], scale: [1, 1.08, 1] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />

        <div className="relative z-10 mx-auto flex max-w-7xl flex-col px-5 py-7 sm:px-8">
          <header className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-deepblue">
                <Sparkles className="h-5 w-5" />
              </span>
              <span className="text-lg font-black">Novoriq</span>
            </Link>
            <nav className="flex items-center gap-3">
              <Button asChild variant="cream" size="sm">
                <Link href="/login">Login</Link>
              </Button>
              <Button asChild variant="default" size="sm">
                <Link href="/register">Create account</Link>
              </Button>
            </nav>
          </header>

          <div className="grid flex-1 items-center gap-10 py-20 lg:grid-cols-[1.02fr_0.98fr]">
            <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55 }}>
              <p className="mb-5 inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-2 text-sm font-bold text-sky-50 ring-1 ring-white/25">
                <CheckCircle2 className="h-4 w-4" />
                Phase 1 reconciliation control center
              </p>
              <h1 className="max-w-4xl text-5xl font-black leading-[1.02] tracking-tight sm:text-6xl lg:text-7xl">
                Controlled reconciliation workflows for accountants and finance teams.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-sky-50">
                Upload files, map columns, normalize records, and prepare clean reconciliation runs.
              </p>
              <div className="mt-9 flex flex-col gap-3 sm:flex-row">
                <Button asChild variant="default" size="lg">
                  <Link href="/register">
                    Create account
                    <ArrowRight className="h-5 w-5" />
                  </Link>
                </Button>
                <Button asChild variant="cream" size="lg">
                  <Link href="/login">Login</Link>
                </Button>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 28 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.1 }}
              className="glass rounded-3xl p-5 shadow-glass"
            >
              <div className="rounded-2xl bg-white p-4 text-ink shadow-soft">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Current run</p>
                    <h2 className="text-xl font-black">June statement cleanup</h2>
                  </div>
                  <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-black text-green-700">Ready</span>
                </div>
                <div className="space-y-3">
                  {["bank_export.csv", "ledger_export.csv", "columns mapped", "1,842 records normalized"].map((item, index) => (
                    <div key={item} className="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50 p-3">
                      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-sky-100 text-sm font-black text-deepblue">
                        {index + 1}
                      </span>
                      <span className="text-sm font-bold text-slate-700">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      <section className="bg-cream px-5 py-16 sm:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-2xl">
            <p className="text-sm font-black uppercase tracking-[0.18em] text-deepblue">Workflow</p>
            <h2 className="mt-3 text-3xl font-black tracking-tight text-ink sm:text-4xl">
              A focused path from source CSVs to reconciliation-ready records.
            </h2>
          </div>
          <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            {steps.map((step) => {
              const Icon = step.icon;
              return (
                <Card key={step.title} className="p-6">
                  <div className={`mb-5 flex h-12 w-12 items-center justify-center rounded-2xl ${step.tone}`}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <h3 className="text-lg font-black">{step.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{step.description}</p>
                </Card>
              );
            })}
          </div>
        </div>
      </section>
    </main>
  );
}
