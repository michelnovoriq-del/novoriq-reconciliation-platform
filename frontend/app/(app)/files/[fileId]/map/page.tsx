"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Loader2, Wand2 } from "lucide-react";
import { useState } from "react";
import { api, type ColumnMapping } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";

const fields: Array<{ key: keyof ColumnMapping; label: string; required?: boolean }> = [
  { key: "date", label: "date", required: true },
  { key: "amount", label: "amount", required: true },
  { key: "reference", label: "reference", required: true },
  { key: "description", label: "description" },
  { key: "customer_name", label: "customer_name" },
  { key: "currency", label: "currency" },
];

export default function MapColumnsPage() {
  const params = useParams<{ fileId: string }>();
  const [mapping, setMapping] = useState<ColumnMapping>({});
  const [error, setError] = useState("");
  const preview = useQuery({ queryKey: ["file-preview", params.fileId], queryFn: () => api.previewFile(params.fileId) });
  const normalize = useMutation({ mutationFn: () => api.normalizeFile(params.fileId, mapping) });

  async function submit() {
    setError("");
    try {
      await normalize.mutateAsync();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not normalize records.");
    }
  }

  if (preview.isLoading) return <Card className="p-6"><Skeleton className="h-96" /></Card>;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-black uppercase tracking-[0.18em] text-deepblue">Column mapping</p>
        <h1 className="text-3xl font-black tracking-tight text-ink">Map to Novoriq standard fields</h1>
      </div>

      <ErrorAlert message={error} />
      {normalize.data ? (
        <Card className={normalize.data.rejected_rows ? "border-amber-200 bg-amber-50 p-5" : "border-green-200 bg-green-50 p-5"}>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              {normalize.data.rejected_rows ? <AlertTriangle className="mt-0.5 h-6 w-6 text-amber-600" /> : <CheckCircle2 className="h-6 w-6 text-green-600" />}
              <div>
                <p className={normalize.data.rejected_rows ? "font-black text-amber-900" : "font-black text-green-900"}>
                  {normalize.data.rejected_rows ? "Normalized with rejected rows" : "Records normalized"}
                </p>
                <p className={normalize.data.rejected_rows ? "text-sm text-amber-800" : "text-sm text-green-700"}>
                  {normalize.data.valid_rows} valid rows saved. {normalize.data.rejected_rows} rows rejected.
                </p>
                {normalize.data.rejected_rows ? <p className="mt-1 text-sm text-amber-800">Some rows could not be normalized. Valid rows were saved. Review rejected records.</p> : null}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {normalize.data.rejected_rows ? <Button asChild variant="outline"><Link href={`/files/${params.fileId}/rejected-records`}>Review rejected rows</Link></Button> : null}
              <Button asChild variant="sky"><Link href="/reconciliation-runs">Create run</Link></Button>
            </div>
          </div>
          {normalize.data.rejected_examples.length ? (
            <div className="mt-4 rounded-xl border border-amber-200 bg-white/70 p-4 text-sm text-amber-950">
              <p className="mb-2 font-black">First rejected rows</p>
              {normalize.data.rejected_examples.map((record) => <p key={record.id}>Row {record.source_row_number}: {record.rejection_reason.replaceAll("_", " ")}</p>)}
            </div>
          ) : null}
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Standard fields</CardTitle>
          <CardDescription>Select the detected source column for each destination field.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {fields.map((field) => (
            <div key={field.key} className="grid gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-4 sm:grid-cols-[220px_1fr] sm:items-center">
              <div>
                <p className="font-mono text-sm font-black text-ink">{field.label}</p>
                <p className="text-xs text-slate-500">{field.required ? "Required" : "Optional context field"}</p>
              </div>
              <select
                className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold outline-none focus:border-skybrand focus:ring-4 focus:ring-sky-100"
                value={mapping[field.key] ?? ""}
                onChange={(event) => setMapping((current) => ({ ...current, [field.key]: event.target.value || null }))}
              >
                <option value="">Do not map</option>
                {preview.data?.columns.map((column) => (
                  <option key={column} value={column}>{column}</option>
                ))}
              </select>
            </div>
          ))}
          <Button variant="sky" onClick={submit} disabled={normalize.isPending || !preview.data}>
            {normalize.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
            Normalize records
          </Button>
        </CardContent>
      </Card>

      {preview.data ? (
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>Sample rows</CardTitle>
            <CardDescription>Use these values to confirm the mapping before normalization.</CardDescription>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-slate-50 text-xs font-black uppercase tracking-wide text-slate-500">
                <tr>{preview.data.columns.map((column) => <th key={column} className="px-5 py-4">{column}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {preview.data.sample_rows.slice(0, 5).map((row, index) => (
                  <tr key={index}>
                    {preview.data.columns.map((column) => (
                      <td key={column} className="max-w-56 truncate px-5 py-4 text-slate-700">{String(row[column] ?? "")}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
