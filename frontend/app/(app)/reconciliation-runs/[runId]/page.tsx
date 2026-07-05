"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Loader2, Play } from "lucide-react";
import { api } from "@/lib/api/client";
import { formatDate } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ErrorAlert } from "@/components/ui/alert";

export default function RunDetailPage() {
  const params = useParams<{ runId: string }>();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const run = useQuery({ queryKey: ["run", params.runId], queryFn: () => api.getRun(params.runId) });
  const matching = useMutation({
    mutationFn: () => api.runMatching(params.runId),
    onSuccess: async () => {
      setMessage("Matching completed. Results are ready to review.");
      await queryClient.invalidateQueries({ queryKey: ["run", params.runId] });
    },
  });

  async function executeMatching() {
    setError("");
    setMessage("");
    try { await matching.mutateAsync(); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not run matching."); }
  }

  if (run.isLoading) return <Card className="p-6"><Skeleton className="h-80" /></Card>;
  if (!run.data) return <Card className="p-6 text-sm text-red-700">Could not load reconciliation run.</Card>;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-black uppercase tracking-[0.18em] text-deepblue">Run detail</p>
        <h1 className="text-3xl font-black tracking-tight text-ink">Run {run.data.id.slice(0, 8)}</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Run summary</CardTitle>
          <CardDescription>Review the selected normalized files and run the deterministic matching engine.</CardDescription>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 md:grid-cols-2">
            {[
              ["Status", <StatusBadge key="status" status={run.data.status} />],
              ["Created", formatDate(run.data.created_at)],
              ["File A", run.data.file_a_id],
              ["File B", run.data.file_b_id],
              ["Organization", run.data.organization_id],
              ["Created by", run.data.created_by_user_id],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                <dt className="text-xs font-black uppercase tracking-wide text-slate-500">{label}</dt>
                <dd className="mt-2 break-all text-sm font-bold text-ink">{value}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>

      <Card className="border-sky-200 bg-sky-50">
        <CardContent className="flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-black text-ink">{run.data.status === "completed" ? "Results are ready" : "Ready to match"}</h2>
            <p className="mt-1 text-sm text-slate-600">{message || "Each File B record can be assigned to at most one File A record."}</p>
            <ErrorAlert message={error} className="mt-3" />
          </div>
          {run.data.status === "completed" ? (
            <Button asChild variant="sky"><Link href={`/reconciliation-runs/${params.runId}/results`}>Review results <ArrowRight className="h-4 w-4" /></Link></Button>
          ) : (
            <Button variant="sky" onClick={executeMatching} disabled={matching.isPending}>
              {matching.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} Run Matching
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
