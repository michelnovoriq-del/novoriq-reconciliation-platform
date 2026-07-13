"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { api, type BillingStatus } from "@/lib/api/client";
import { useAuth } from "@/lib/hooks/use-auth";

export default function BillingReturnPage() {
  const { refreshAccount } = useAuth();
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [attempts, setAttempts] = useState(0);
  async function check() {
    const next = await api.getBillingStatus(); setStatus(next); setAttempts((n) => n + 1);
    if (next.plan_code !== "free") await refreshAccount();
  }
  useEffect(() => { void check(); }, []);
  useEffect(() => {
    if (!status || status.plan_code !== "free" || status.pending_whop_link || attempts >= 6) return;
    const timer = window.setTimeout(() => void check(), 10_000); return () => window.clearTimeout(timer);
  }, [status, attempts]);
  const active = status && status.plan_code !== "free";
  return <ProtectedRoute><main className="min-h-screen bg-cream px-5 py-16"><Card className="mx-auto max-w-xl p-8">
    <h1 className="text-3xl font-black">{active ? `Your ${status.plan_name} plan is active.` : "Payment submitted"}</h1>
    <p className="mt-4 text-slate-600">{active ? "Your Novoriq access has refreshed." : status?.pending_whop_link ? "We could not link the membership automatically. Confirm that Whop used your verified Novoriq email." : "Novoriq is verifying your Whop membership. This usually updates shortly."}</p>
    <div className="mt-7 flex gap-3">{active ? <Button asChild variant="sky"><Link href="/dashboard">Go to Dashboard</Link></Button> : <Button onClick={() => void check()} variant="sky">Check my access</Button>}<Button asChild variant="outline"><Link href="/support">Contact support</Link></Button></div>
  </Card></main></ProtectedRoute>;
}
