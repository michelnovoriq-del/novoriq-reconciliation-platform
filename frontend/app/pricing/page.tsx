"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, Check, ExternalLink, Loader2, RefreshCw, ShieldCheck, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/hooks/use-auth";
import { PublicFooter } from "@/components/layout/public-footer";
import { PublicHeader } from "@/components/layout/public-header";

const supportEmail = "michelnovoriq@gmail.com";

const checkoutUrls = {
  professional: process.env.NEXT_PUBLIC_WHOP_PROFESSIONAL_CHECKOUT_URL ?? "",
  firm: process.env.NEXT_PUBLIC_WHOP_FIRM_CHECKOUT_URL ?? "",
  enterprise: process.env.NEXT_PUBLIC_WHOP_ENTERPRISE_CHECKOUT_URL ?? "",
};

const plans = [
  {
    code: "free",
    name: "Free Forever",
    price: "$0",
    cadence: "Forever",
    badge: "Available now",
    description: "Full core reconciliation workflow with volume limits.",
    features: [
      "2 reconciliation runs/month",
      "2 files/run",
      "2,500 rows/file",
      "1 user",
      "1 workspace",
      "Core matching and review",
      "CSV export",
      "7-day detailed history",
    ],
  },
  {
    code: "professional",
    name: "Professional",
    price: "$279",
    cadence: "per month",
    badge: undefined,
    description: "For finance teams running recurring reconciliation operations.",
    features: [
      "50 reconciliation runs/month",
      "3 files/run",
      "25,000 rows/file",
      "3 users",
      "20 client workspaces",
      "12-month detailed history",
      "Full audit history",
      "Priority email support",
      "AI mapping coming soon",
    ],
  },
  {
    code: "firm",
    name: "Firm",
    price: "$499",
    cadence: "per month",
    badge: "Firm favorite",
    description: "Best for accounting firms managing multiple clients and team members.",
    features: [
      "150 reconciliation runs/month",
      "4 files/run",
      "50,000 rows/file",
      "10 users",
      "75 client workspaces",
      "24-month detailed history",
      "Priority onboarding",
      "Advanced approvals coming soon",
      "AI explanations coming soon",
    ],
  },
  {
    code: "enterprise",
    name: "Enterprise",
    price: "$799",
    cadence: "per month",
    badge: "Tier 4",
    description: "Higher-volume reconciliation capacity for larger operating teams.",
    features: [
      "400 reconciliation runs/month",
      "6 files/run",
      "150,000 rows/file",
      "25 users",
      "250 client workspaces",
      "36-month detailed history",
      "Dedicated success support",
      "Audit export coming soon",
      "Advanced approvals coming soon",
    ],
  },
] as const;

type PaidPlanCode = "professional" | "firm" | "enterprise";

export default function PricingPage() {
  const { user, account, isAuthenticated, refreshAccount } = useAuth();
  const [intendedPlan, setIntendedPlan] = useState<string | null>(null);
  useEffect(() => setIntendedPlan(new URLSearchParams(window.location.search).get("plan")), []);
  const [selectedPlan, setSelectedPlan] = useState<(typeof plans)[number] | null>(null);
  const [confirmedEmail, setConfirmedEmail] = useState(false);
  const billingStatus = useQuery({
    queryKey: ["billing", "status"],
    queryFn: api.getBillingStatus,
    enabled: isAuthenticated,
  });
  const syncMutation = useMutation({
    mutationFn: api.syncWhopAccess,
    onSuccess: async (status) => { await billingStatus.refetch(); await refreshAccount(); return status; },
  });

  const selectedCheckoutUrl = useMemo(() => {
    if (!selectedPlan || selectedPlan.code === "free") return "";
    return checkoutUrls[selectedPlan.code as PaidPlanCode];
  }, [selectedPlan]);

  function beginUpgrade(plan: (typeof plans)[number]) {
    if (plan.code === "free") return;
    setConfirmedEmail(false);
    setSelectedPlan(plan);
  }

  function continueToWhop() {
    if (!confirmedEmail || !selectedCheckoutUrl) return;
    window.open(selectedCheckoutUrl, "_blank", "noopener,noreferrer");
  }

  return (
    <div className="min-h-screen bg-[#FAF3E7] text-[#111827]">
      <PublicHeader />
      <main>
      <section className="px-5 py-12 sm:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-3xl">
            <p className="text-sm font-black uppercase text-[#0369A1]">Pricing</p>
            <h1 className="mt-3 text-4xl font-black tracking-tight sm:text-5xl">Simple plans for growing reconciliation workflows</h1>
            <p className="mt-4 text-base leading-7 text-[#4B5563]">
              Free Forever includes the full core workflow. Paid plans are handled through Whop-hosted checkout.
            </p>
          </div>

          {billingStatus.data?.message ? (
            <div className="mt-8 rounded-lg border border-[#F59E0B]/30 bg-white px-4 py-3 text-sm font-semibold text-[#4B5563]">
              {billingStatus.data.message}{" "}
              <a href={`mailto:${supportEmail}`} className="text-[#0369A1] underline">{supportEmail}</a>
            </div>
          ) : null}

          <div className="mt-8 flex flex-wrap items-center gap-3">
            {isAuthenticated ? (
              <Button
                variant="outline"
                onClick={() => syncMutation.mutate()}
                disabled={syncMutation.isPending}
              >
                {syncMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                Check my access
              </Button>
            ) : null}
            {billingStatus.data ? (
              <Badge tone={billingStatus.data.pending_whop_link ? "amber" : "green"}>
                Current plan: {billingStatus.data.plan_name}
              </Badge>
            ) : null}
          </div>

          <div className="mt-8 grid gap-4 lg:grid-cols-4">
            {plans.map((plan) => {
              const isFree = plan.code === "free";
              const checkoutUrl = !isFree ? checkoutUrls[plan.code as PaidPlanCode] : "";
              const unavailable = !isFree && !checkoutUrl;
              const currentCode = account?.subscription.plan_code ?? billingStatus.data?.plan_code;
              const isCurrent = currentCode === plan.code;
              const isPaid = currentCode === "professional" || currentCode === "firm" || currentCode === "enterprise";
              const selected = intendedPlan === plan.code;
              return (
                <Card key={plan.code} className={`flex rounded-lg bg-[#FFF8ED] p-5 ${selected ? "ring-2 ring-skybrand" : ""}`}>
                  <div className="flex min-h-[590px] w-full flex-col">
                    <div className="flex min-h-24 items-start justify-between gap-3">
                      <div>
                        <h2 className="text-xl font-black">{plan.name}</h2>
                        <p className="mt-2 text-sm leading-6 text-[#4B5563]">{plan.description}</p>
                      </div>
                      {isCurrent ? <Badge tone="green">Current plan</Badge> : plan.badge ? <Badge tone={plan.code === "free" ? "green" : "sky"}>{plan.badge}</Badge> : null}
                    </div>
                    <div className="mt-6">
                      <span className="text-4xl font-black">{plan.price}</span>
                      <span className="ml-2 text-sm font-bold text-[#4B5563]">{plan.cadence}</span>
                    </div>
                    <ul className="mt-6 flex-1 space-y-3">
                      {plan.features.map((feature) => (
                        <li key={feature} className="flex gap-2 text-sm leading-5 text-[#4B5563]">
                          <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#10B981]" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                    {isFree ? (
                      <Button asChild variant="sky" className="mt-6 w-full">
                        <Link href={isAuthenticated ? "/dashboard" : "/register?returnTo=%2Fdashboard"}>
                          {isAuthenticated ? (isPaid ? "Current paid plan active" : "Go to Dashboard") : "Start Free"}
                          <ArrowRight className="h-4 w-4" />
                        </Link>
                      </Button>
                    ) : isCurrent ? (
                      <Button className="mt-6 w-full" variant="outline" disabled>Current plan</Button>
                    ) : isAuthenticated ? (
                      <>
                        <Button className="mt-6 w-full" variant="sky" onClick={() => beginUpgrade(plan)} disabled={unavailable}>
                          Upgrade with Whop
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                        {unavailable ? (
                          <p className="mt-3 text-xs font-semibold text-[#EF4444]">
                            Checkout is temporarily unavailable. Contact Novoriq support.
                          </p>
                        ) : null}
                      </>
                    ) : (
                      <Button asChild className="mt-6 w-full" variant="sky">
                        <Link href={`/login?returnTo=${encodeURIComponent(`/pricing?plan=${plan.code}`)}`}>
                          Upgrade with Whop
                          <ArrowRight className="h-4 w-4" />
                        </Link>
                      </Button>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      </section>
      </main>

      {selectedPlan ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#111827]/50 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-soft">
            <div className="flex items-start justify-between gap-3">
              <div>
                <Badge tone="sky">{selectedPlan.name}</Badge>
                <h2 className="mt-3 text-2xl font-black">Prepare Whop checkout</h2>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setSelectedPlan(null)} aria-label="Close">
                <X className="h-4 w-4" />
              </Button>
            </div>
            <p className="mt-4 text-sm leading-6 text-[#4B5563]">
              Use the same email address on Whop that you use for your Novoriq account. Novoriq will verify your Whop membership and apply the plan to your organization.
            </p>
            <div className="mt-4 rounded-lg bg-[#E0F2FE] p-4">
              <p className="text-xs font-black uppercase text-[#0369A1]">Signed in as</p>
              <p className="mt-1 break-all text-sm font-bold">{user?.email}</p>
            </div>
            <label className="mt-5 flex gap-3 text-sm font-semibold text-[#111827]">
              <input
                type="checkbox"
                checked={confirmedEmail}
                onChange={(event) => setConfirmedEmail(event.target.checked)}
                className="mt-1 h-4 w-4"
              />
              <span>I will use this same email address during Whop checkout.</span>
            </label>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <Button variant="sky" className="flex-1" disabled={!confirmedEmail || !selectedCheckoutUrl} onClick={continueToWhop}>
                <ShieldCheck className="h-4 w-4" />
                Continue to Whop
              </Button>
              <Button variant="outline" className="flex-1" onClick={() => setSelectedPlan(null)}>Cancel</Button>
            </div>
          </div>
        </div>
      ) : null}
      <PublicFooter />
    </div>
  );
}
