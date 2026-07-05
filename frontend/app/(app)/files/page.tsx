"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Eye, Files, PlusCircle, Wand2 } from "lucide-react";
import { api } from "@/lib/api/client";
import { formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/badge";

export default function FilesPage() {
  const files = useQuery({ queryKey: ["files"], queryFn: api.listFiles });

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm font-black uppercase tracking-[0.18em] text-deepblue">Files</p>
          <h1 className="text-3xl font-black tracking-tight text-ink">Uploaded files</h1>
        </div>
        <Button asChild variant="sky"><Link href="/files/upload"><PlusCircle className="h-4 w-4" />Upload file</Link></Button>
      </div>

      {files.isLoading ? (
        <Card className="p-5"><Skeleton className="h-72" /></Card>
      ) : files.data?.length ? (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-slate-50 text-xs font-black uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-4">Filename</th>
                  <th className="px-5 py-4">File type</th>
                  <th className="px-5 py-4">Row count</th>
                  <th className="px-5 py-4">Status</th>
                  <th className="px-5 py-4">Uploaded date</th>
                  <th className="px-5 py-4">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {files.data.map((file) => (
                  <tr key={file.id}>
                    <td className="px-5 py-4 font-bold text-ink">{file.original_filename}</td>
                    <td className="px-5 py-4 text-slate-600">{file.file_type}</td>
                    <td className="px-5 py-4 text-slate-600">{file.row_count ?? "Pending"}</td>
                    <td className="px-5 py-4"><StatusBadge status={file.status} /></td>
                    <td className="px-5 py-4 text-slate-600">{formatDate(file.created_at)}</td>
                    <td className="px-5 py-4">
                      <div className="flex gap-2">
                        <Button asChild variant="outline" size="sm"><Link href={`/files/${file.id}/preview`}><Eye className="h-4 w-4" />Preview</Link></Button>
                        <Button asChild variant="outline" size="sm"><Link href={`/files/${file.id}/map`}><Wand2 className="h-4 w-4" />Normalize</Link></Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <EmptyState icon={Files} title="No uploaded files" description="Upload a CSV file to preview, map, and normalize it." action={<Button asChild variant="sky"><Link href="/files/upload"><PlusCircle className="h-4 w-4" />Upload file</Link></Button>} />
      )}
    </div>
  );
}
