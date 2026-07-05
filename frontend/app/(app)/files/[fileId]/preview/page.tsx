"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Columns3 } from "lucide-react";
import { api } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function FilePreviewPage() {
  const params = useParams<{ fileId: string }>();
  const preview = useQuery({ queryKey: ["file-preview", params.fileId], queryFn: () => api.previewFile(params.fileId) });

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm font-black uppercase tracking-[0.18em] text-deepblue">Preview</p>
          <h1 className="text-3xl font-black tracking-tight text-ink">Detected file rows</h1>
        </div>
        <Button asChild variant="sky"><Link href={`/files/${params.fileId}/map`}>Map columns<ArrowRight className="h-4 w-4" /></Link></Button>
      </div>

      {preview.isLoading ? (
        <Card className="p-6"><Skeleton className="h-96" /></Card>
      ) : preview.data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="p-5">
              <p className="text-sm font-bold text-slate-500">File ID</p>
              <p className="mt-2 break-all font-mono text-sm text-ink">{preview.data.file_id}</p>
            </Card>
            <Card className="p-5">
              <p className="text-sm font-bold text-slate-500">Detected columns</p>
              <p className="mt-2 text-2xl font-black text-ink">{preview.data.columns.length}</p>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Columns3 className="h-5 w-5 text-deepblue" />Detected columns</CardTitle>
              <CardDescription>These columns can be mapped to Novoriq standard fields.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {preview.data.columns.map((column) => (
                  <span key={column} className="rounded-full bg-sky-100 px-3 py-1 text-xs font-bold text-deepblue">{column}</span>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="overflow-hidden">
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
        </>
      ) : (
        <Card className="p-6 text-sm text-red-700">Could not load preview.</Card>
      )}
    </div>
  );
}
