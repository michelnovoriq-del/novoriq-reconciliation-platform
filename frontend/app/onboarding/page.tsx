"use client";

import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAuth } from "@/lib/hooks/use-auth";

export default function OnboardingPage() {
  const { account } = useAuth();
  return <ProtectedRoute><main className="min-h-screen bg-cream px-5 py-16">
    <Card className="mx-auto max-w-2xl p-8">
      <CheckCircle2 className="h-10 w-10 text-emerald-500" />
      <h1 className="mt-5 text-3xl font-black">Welcome to Novoriq</h1>
      <p className="mt-3 text-slate-600">Your {account?.subscription.plan_name ?? "Free Forever"} workspace is ready.</p>
      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl bg-sky-50 p-4 font-bold">2 runs / month</div>
        <div className="rounded-xl bg-sky-50 p-4 font-bold">2 files / run</div>
        <div className="rounded-xl bg-sky-50 p-4 font-bold">2,500 rows / file</div>
      </div>
      <p className="mt-7 text-sm font-bold text-slate-700">Upload → Map → Normalize → Match → Review → Export</p>
      <div className="mt-7 flex gap-3"><Button asChild variant="sky"><Link href="/files/upload">Start first reconciliation</Link></Button><Button asChild variant="outline"><Link href="/dashboard">Skip to dashboard</Link></Button></div>
    </Card>
  </main></ProtectedRoute>;
}
