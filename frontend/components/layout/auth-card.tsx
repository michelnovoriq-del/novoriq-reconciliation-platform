import Link from "next/link";
import { Check, Sparkles } from "lucide-react";

export function AuthCard({ title, description, children, footer, mode }: {
  title: string;
  description: string;
  children: React.ReactNode;
  footer: React.ReactNode;
  mode: "login" | "register";
}) {
  const register = mode === "register";
  return (
    <main className="min-h-screen bg-gradient-to-br from-cream via-white to-sky-100/70 p-4 sm:p-6 lg:flex lg:items-center lg:p-10">
      <div className="mx-auto grid w-full max-w-6xl overflow-hidden rounded-[2rem] border border-white/80 bg-white/60 shadow-soft backdrop-blur lg:grid-cols-[1.05fr_0.95fr]">
        <section className="relative overflow-hidden bg-deepblue px-6 py-8 text-white sm:px-10 lg:flex lg:min-h-[680px] lg:flex-col lg:justify-between lg:p-12">
          <div className="absolute -right-20 top-24 h-72 w-72 rounded-full bg-skybrand/30 blur-3xl" />
          <Link href="/" className="relative z-10 flex w-fit items-center gap-3 rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-deepblue"><Sparkles className="h-5 w-5" /></span>
            <span className="text-lg font-black">Novoriq</span>
          </Link>
          <div className="relative z-10 mt-8 max-w-xl lg:my-auto">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-200">Controlled reconciliation</p>
            <h2 className="mt-3 text-3xl font-black leading-tight tracking-tight sm:text-4xl">
              {register ? "Create your reconciliation workspace" : "Return to a workflow built for review."}
            </h2>
            <p className="mt-4 leading-7 text-sky-50">
              {register
                ? "Start with Novoriq Free Forever and run a controlled CSV and Excel reconciliation workflow for your team."
                : "Keep mapping, matching, reviewing, and approving your financial files in one focused workspace."}
            </p>
            <ul className="mt-6 hidden space-y-3 text-sm text-sky-50 sm:block">
              {["Map and normalize financial files", "Review likely matches and exceptions", "Approve results before export"].map((benefit) => (
                <li key={benefit} className="flex items-center gap-3"><Check className="h-4 w-4 text-sky-300" />{benefit}</li>
              ))}
            </ul>
          </div>
          {register && <div className="relative z-10 mt-7 flex flex-wrap gap-x-5 gap-y-2 text-sm text-sky-50"><strong className="text-white">Free Forever</strong><span>2 reconciliation runs each month</span><span>No payment required</span></div>}
        </section>
        <section className="flex items-center justify-center p-5 sm:p-9 lg:p-12">
          <div className="w-full max-w-[34rem] rounded-3xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-900/5 sm:p-8">
            <header className="mb-7">
              <h1 className="text-3xl font-black tracking-tight text-ink">{title}</h1>
              <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
            </header>
            {children}
            <div className="mt-6 text-center text-sm text-slate-600">{footer}</div>
          </div>
        </section>
      </div>
    </main>
  );
}
