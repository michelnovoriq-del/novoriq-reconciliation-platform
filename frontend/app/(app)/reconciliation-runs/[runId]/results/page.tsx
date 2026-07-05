"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Download, Loader2, X } from "lucide-react";
import { api, MatchResult, NormalizedRecord } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/alert";
import { StatusBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

function RecordCell({ label, record }: { label: string; record: NormalizedRecord | null }) {
  return (
    <div className="rounded-xl bg-white/80 p-3">
      <p className="text-xs font-black uppercase tracking-wide text-slate-500">{label}</p>
      {record ? <div className="mt-2 space-y-1 text-sm"><p className="font-bold text-ink">{record.reference || "No reference"}</p><p>{record.transaction_date || "No date"} · {record.amount ?? "No amount"}</p><p className="text-slate-500">{record.customer_name || record.description || "No description"}</p></div> : <p className="mt-2 text-sm text-slate-400">No paired record</p>}
    </div>
  );
}

function ResultRow({ result, onReview, pending }: { result: MatchResult; onReview: (id: string, action: "approve" | "reject") => void; pending: boolean }) {
  const reviewable = ["matched", "possible_match", "approved", "rejected"].includes(result.status);
  return (
    <div className="rounded-2xl border border-black/5 bg-white/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3"><div className="flex items-center gap-2"><StatusBadge status={result.status} /><span className="text-sm font-black">{result.confidence_score}% confidence</span></div><span className="text-xs text-slate-500">Amount diff: {result.amount_difference ?? "n/a"} · Date diff: {result.date_difference_days ?? "n/a"}</span></div>
      <p className="mt-3 text-sm text-slate-700">{result.match_reason}</p>
      <div className="mt-4 grid gap-3 md:grid-cols-2"><RecordCell label="File A" record={result.file_a_record} /><RecordCell label="File B" record={result.file_b_record} /></div>
      {reviewable && <div className="mt-4 flex gap-2"><Button size="sm" variant="sky" disabled={pending || result.status === "approved"} onClick={() => onReview(result.id, "approve")}><Check className="h-4 w-4" />Approve</Button><Button size="sm" variant="danger" disabled={pending || result.status === "rejected"} onClick={() => onReview(result.id, "reject")}><X className="h-4 w-4" />Reject</Button></div>}
    </div>
  );
}

export default function ResultsPage() {
  const params = useParams<{ runId: string }>();
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);
  const results = useQuery({ queryKey: ["results", params.runId], queryFn: () => api.getReconciliationResults(params.runId) });
  const review = useMutation({ mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" }) => action === "approve" ? api.approveMatch(id) : api.rejectMatch(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["results", params.runId] }) });
  async function onReview(id: string, action: "approve" | "reject") { setError(""); try { await review.mutateAsync({ id, action }); } catch (err) { setError(err instanceof Error ? err.message : "Could not save review."); } }
  async function exportCsv() { setError(""); setExporting(true); try { const blob = await api.exportReconciliationRun(params.runId); const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `reconciliation_run_${params.runId}.csv`; anchor.click(); URL.revokeObjectURL(url); } catch (err) { setError(err instanceof Error ? err.message : "Could not export results."); } finally { setExporting(false); } }
  if (results.isLoading) return <Card className="p-6"><Skeleton className="h-96" /></Card>;
  if (!results.data) return <ErrorAlert message={results.error instanceof Error ? results.error.message : "Could not load results."} />;
  const sections = [
    { title: "Green - High Confidence Matches", items: results.data.green_matches, className: "border-green-200 bg-green-50" },
    { title: "Yellow - Possible Matches", items: results.data.yellow_possible_matches, className: "border-amber-200 bg-amber-50" },
    { title: "Red - Unmatched / Rejected", items: results.data.red_unmatched, className: "border-red-200 bg-red-50" },
  ];
  const mostlyRed = results.data.summary.total_matches > 0
    && results.data.summary.red_count / results.data.summary.total_matches >= 0.8;
  return <div className="space-y-6"><div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-black uppercase tracking-[0.18em] text-deepblue">Review</p><h1 className="text-3xl font-black tracking-tight text-ink">Reconciliation results</h1><p className="mt-2 text-sm text-slate-600">{results.data.summary.total_matches} results · {results.data.summary.approved_count} approved · {results.data.summary.rejected_count} rejected</p></div><Button variant="sky" disabled={exporting} onClick={exportCsv}>{exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}Export CSV</Button></div><ErrorAlert message={error} />{mostlyRed ? <Card className="border-amber-200 bg-amber-50"><CardContent className="p-4 text-sm font-semibold text-amber-900">These files may be unrelated or mapped incorrectly. Review column mappings before relying on results.</CardContent></Card> : null}{sections.map((section) => <Card key={section.title} className={section.className}><CardHeader><CardTitle>{section.title} ({section.items.length})</CardTitle></CardHeader><CardContent className="space-y-3">{section.items.length ? section.items.map((item) => <ResultRow key={item.id} result={item} pending={review.isPending} onReview={onReview} />) : <p className="text-sm text-slate-500">No results in this bucket.</p>}</CardContent></Card>)}</div>;
}
