"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, Loader2, PlusCircle } from "lucide-react";
import { api } from "@/lib/api/client";
import { formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorAlert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export default function RunsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const files = useQuery({ queryKey: ["files"], queryFn: api.listFiles });
  const runs = useQuery({ queryKey: ["runs"], queryFn: api.listRuns });
  const normalizedFiles = useMemo(
    () => files.data?.filter((file) => ["normalized", "normalized_with_rejections"].includes(file.status)) ?? [],
    [files.data],
  );
  const [fileA, setFileA] = useState("");
  const [fileB, setFileB] = useState("");
  const [error, setError] = useState("");
  const createRun = useMutation({
    mutationFn: () => api.createRun({ file_a_id: fileA, file_b_id: fileB }),
    onSuccess: async (run) => {
      setFileA("");
      setFileB("");
      await queryClient.invalidateQueries({ queryKey: ["runs"] });
      router.push(`/reconciliation-runs/${run.id}`);
    },
  });

  async function submit() {
    setError("");
    if (!fileA || !fileB || fileA === fileB) {
      setError("Choose two different normalized files.");
      return;
    }
    try {
      await createRun.mutateAsync();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create reconciliation run.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-black uppercase tracking-[0.18em] text-deepblue">Runs</p>
        <h1 className="text-3xl font-black tracking-tight text-ink">Reconciliation runs</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Create reconciliation run</CardTitle>
          <CardDescription>Select two different normalized files, then continue to deterministic matching.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ErrorAlert message={error} />
          <div className="grid gap-4 md:grid-cols-2">
            {[{ value: fileA, setter: setFileA, label: "File A" }, { value: fileB, setter: setFileB, label: "File B" }].map((field) => (
              <div key={field.label} className="space-y-2">
                <label className="text-sm font-bold text-slate-700">{field.label}</label>
                <select
                  className="h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold outline-none focus:border-skybrand focus:ring-4 focus:ring-sky-100"
                  value={field.value}
                  onChange={(event) => field.setter(event.target.value)}
                >
                  <option value="">Select normalized file</option>
                  {normalizedFiles.map((file) => (
                    <option key={file.id} value={file.id}>{file.original_filename}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          <Button variant="sky" onClick={submit} disabled={createRun.isPending || normalizedFiles.length < 2}>
            {createRun.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <PlusCircle className="h-4 w-4" />}
            Create run
          </Button>
        </CardContent>
      </Card>

      {runs.isLoading ? (
        <Card className="p-6"><Skeleton className="h-72" /></Card>
      ) : runs.data?.length ? (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-slate-50 text-xs font-black uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-4">Run</th>
                  <th className="px-5 py-4">File A</th>
                  <th className="px-5 py-4">File B</th>
                  <th className="px-5 py-4">Status</th>
                  <th className="px-5 py-4">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {runs.data.map((run) => (
                  <tr key={run.id}>
                    <td className="px-5 py-4 font-bold text-deepblue"><Link href={`/reconciliation-runs/${run.id}`}>{run.id.slice(0, 8)}</Link></td>
                    <td className="px-5 py-4 font-mono text-xs text-slate-600">{run.file_a_id.slice(0, 8)}</td>
                    <td className="px-5 py-4 font-mono text-xs text-slate-600">{run.file_b_id.slice(0, 8)}</td>
                    <td className="px-5 py-4"><StatusBadge status={run.status} /></td>
                    <td className="px-5 py-4 text-slate-600">{formatDate(run.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <EmptyState icon={BarChart3} title="No reconciliation runs" description="Normalize two files, then create a run to prepare for matching." />
      )}
    </div>
  );
}
