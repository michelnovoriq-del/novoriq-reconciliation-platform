"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, AlertTriangle } from "lucide-react";

import { api } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";

export default function RejectedRecordsPage() {
  const params = useParams<{ fileId: string }>();
  const rejected = useQuery({
    queryKey: ["rejected-records", params.fileId],
    queryFn: () => api.getRejectedRecords(params.fileId),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-black uppercase tracking-[0.18em] text-amber-700">Data quality</p>
          <h1 className="text-3xl font-black tracking-tight text-ink">Rejected records</h1>
          <p className="mt-1 text-sm text-slate-600">Review rows that could not be normalized. The first 100 are shown.</p>
        </div>
        <Button asChild variant="outline"><Link href={`/files/${params.fileId}/map`}><ArrowLeft className="h-4 w-4" />Back to mapping</Link></Button>
      </div>

      <ErrorAlert message={rejected.error instanceof Error ? rejected.error.message : undefined} />
      {rejected.isLoading ? <Card className="p-6"><Skeleton className="h-72" /></Card> : null}
      {rejected.data ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><AlertTriangle className="h-5 w-5 text-amber-600" />{rejected.data.total_rejected} rejected rows</CardTitle>
            <CardDescription>Fix these values in the source file, then normalize it again.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {rejected.data.records.map((record) => (
              <article key={record.id} className="rounded-2xl border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-black text-ink">Row {record.source_row_number}</p>
                  <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">{record.rejection_reason.replaceAll("_", " ")}</span>
                </div>
                {record.field_errors ? <div className="mt-3 text-sm text-red-700">{Object.entries(record.field_errors).map(([field, message]) => <p key={field}><strong>{field}:</strong> {message}</p>)}</div> : null}
                <pre className="mt-3 overflow-x-auto rounded-xl bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(record.raw_data, null, 2)}</pre>
              </article>
            ))}
            {!rejected.data.records.length ? <p className="text-sm text-slate-600">This file has no rejected records.</p> : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
