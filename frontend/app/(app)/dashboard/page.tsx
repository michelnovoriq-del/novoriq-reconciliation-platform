"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, FileUp, Files, PlusCircle } from "lucide-react";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/hooks/use-auth";
import { formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/badge";

export default function DashboardPage() {
  const { user } = useAuth();
  const files = useQuery({ queryKey: ["files"], queryFn: api.listFiles });
  const runs = useQuery({ queryKey: ["runs"], queryFn: api.listRuns });
  const entitlements = useQuery({ queryKey: ["billing", "current"], queryFn: api.getCurrentEntitlements });
  const billingStatus = useQuery({ queryKey: ["billing", "status"], queryFn: api.getBillingStatus });
  const usage = entitlements.data?.usage;
  const plan = entitlements.data?.plan;
  const runLimit = plan?.monthly_run_limit ?? 1;
  const runUsed = usage?.reconciliation_runs_used ?? 0;
  const runPercent = Math.min(100, Math.round((runUsed / runLimit) * 100));

  return (
    <div className="space-y-8">
      <div className="rounded-3xl bg-skybrand p-7 text-white shadow-glass">
        <p className="text-sm font-bold text-sky-100">Dashboard</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight sm:text-4xl">
          Welcome{user?.full_name ? `, ${user.full_name}` : ""}.
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-sky-50">
          Signed in as {user?.email}. Upload source files, preview detected rows, map columns, and prepare clean reconciliation runs.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {[
          { href: "/files/upload", title: "Upload files", description: "Add a CSV source file.", icon: FileUp },
          { href: "/files", title: "View uploaded files", description: "Preview and normalize files.", icon: Files },
          { href: "/reconciliation-runs", title: "View reconciliation runs", description: "Inspect prepared runs.", icon: BarChart3 },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href}>
              <Card className="h-full p-5 transition hover:-translate-y-0.5 hover:border-skybrand">
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-100 text-deepblue">
                  <Icon className="h-5 w-5" />
                </div>
                <h2 className="font-black text-ink">{item.title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
              </Card>
            </Link>
          );
        })}
      </div>

      <Card className="p-5">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm font-black text-deepblue">Current plan</p>
            <h2 className="mt-1 text-2xl font-black text-ink">{plan?.name ?? "Loading"}</h2>
            {billingStatus.data ? (
              <p className="mt-1 text-xs font-bold text-slate-500">
                {billingStatus.data.whop_linked ? "Whop billing linked" : billingStatus.data.pending_whop_link ? "Whop link pending" : "Free Forever entitlement"}
              </p>
            ) : null}
            <p className="mt-2 text-sm text-slate-600">
              {runUsed} of {runLimit} reconciliation runs used. {entitlements.data?.remaining_reconciliation_runs ?? 0} run
              {(entitlements.data?.remaining_reconciliation_runs ?? 0) === 1 ? "" : "s"} remaining this month.
            </p>
          </div>
          <Button asChild variant="outline"><Link href="/pricing">Upgrade / Request more capacity</Link></Button>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <div>
            <div className="mb-2 flex justify-between text-xs font-bold text-slate-600"><span>Reconciliation runs</span><span>{runPercent}%</span></div>
            <div className="h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-skybrand" style={{ width: `${runPercent}%` }} /></div>
          </div>
          <div>
            <div className="mb-2 flex justify-between text-xs font-bold text-slate-600"><span>Uploaded files</span><span>{usage?.files_uploaded ?? 0}</span></div>
            <div className="h-2 rounded-full bg-slate-100"><div className="h-2 w-1/3 rounded-full bg-emerald-500" /></div>
          </div>
          <div>
            <div className="mb-2 flex justify-between text-xs font-bold text-slate-600"><span>Rows processed</span><span>{usage?.rows_processed ?? 0}</span></div>
            <div className="h-2 rounded-full bg-slate-100"><div className="h-2 w-1/4 rounded-full bg-amber-500" /></div>
          </div>
        </div>
        {entitlements.data?.remaining_reconciliation_runs === 0 ? (
          <p className="mt-4 rounded-xl bg-amber-50 p-3 text-sm font-semibold text-amber-900">
            You have reached your {plan?.name} monthly reconciliation limit. Your allowance resets on{" "}
            {usage ? formatDate(usage.period_end) : "the next billing period"}.
          </p>
        ) : null}
        {billingStatus.data?.message ? (
          <p className="mt-4 rounded-xl bg-sky-50 p-3 text-sm font-semibold text-deepblue">
            {billingStatus.data.message}
          </p>
        ) : null}
      </Card>

      <Card className="border-0 bg-cream">
        <CardHeader><CardTitle>MVP workflow</CardTitle><CardDescription>From source data to an auditable reconciliation export.</CardDescription></CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">{["Upload files", "Normalize records", "Create run", "Run matching", "Review results", "Export CSV"].map((step, index) => <div key={step} className="rounded-xl bg-white p-3"><span className="text-xs font-black text-skybrand">{index + 1}</span><p className="mt-1 text-sm font-bold text-ink">{step}</p></div>)}</CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent uploaded files</CardTitle>
            <CardDescription>Files available for preview and normalization.</CardDescription>
          </CardHeader>
          <CardContent>
            {files.isLoading ? (
              <div className="space-y-3"><Skeleton className="h-14" /><Skeleton className="h-14" /></div>
            ) : files.data?.length ? (
              <div className="space-y-3">
                {files.data.slice(0, 5).map((file) => (
                  <Link key={file.id} href={`/files/${file.id}/preview`} className="flex items-center justify-between rounded-xl border border-slate-100 p-3 hover:bg-sky-50">
                    <div>
                      <p className="font-bold text-ink">{file.original_filename}</p>
                      <p className="text-xs text-slate-500">{formatDate(file.created_at)}</p>
                    </div>
                    <StatusBadge status={file.status} />
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState icon={Files} title="No files yet" description="Upload your first CSV to start the workflow." action={<Button asChild variant="sky"><Link href="/files/upload"><PlusCircle className="h-4 w-4" />Upload</Link></Button>} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent reconciliation runs</CardTitle>
            <CardDescription>Created after two normalized files are ready.</CardDescription>
          </CardHeader>
          <CardContent>
            {runs.isLoading ? (
              <div className="space-y-3"><Skeleton className="h-14" /><Skeleton className="h-14" /></div>
            ) : runs.data?.length ? (
              <div className="space-y-3">
                {runs.data.slice(0, 5).map((run) => (
                  <Link key={run.id} href={`/reconciliation-runs/${run.id}`} className="flex items-center justify-between rounded-xl border border-slate-100 p-3 hover:bg-sky-50">
                    <div>
                      <p className="font-bold text-ink">Run {run.id.slice(0, 8)}</p>
                      <p className="text-xs text-slate-500">{formatDate(run.created_at)}</p>
                    </div>
                    <StatusBadge status={run.status} />
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState icon={BarChart3} title="No runs yet" description="Normalize two files and create your first reconciliation run." />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
