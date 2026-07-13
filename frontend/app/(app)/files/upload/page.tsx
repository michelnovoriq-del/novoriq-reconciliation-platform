"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileUp, Loader2 } from "lucide-react";
import { api, type UploadedFile } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/alert";

export default function UploadPage() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<File | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [uploaded, setUploaded] = useState<UploadedFile | null>(null);
  const [error, setError] = useState("");
  const upload = useMutation({
    mutationFn: api.uploadFile,
    onSuccess: async (file) => {
      setUploaded(file);
      await queryClient.invalidateQueries({ queryKey: ["files"] });
    },
  });

  async function submit() {
    if (!selected) return;
    setError("");
    try {
      await upload.mutateAsync({ file: selected, prohibitedDataAcknowledged: acknowledged });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <p className="text-sm font-black uppercase tracking-[0.18em] text-deepblue">Upload</p>
        <h1 className="text-3xl font-black tracking-tight text-ink">Upload a CSV file</h1>
      </div>

      <Card className="p-6">
        <ErrorAlert message={error} className="mb-5" />
        <label
          className="flex min-h-72 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-sky-200 bg-sky-50/60 p-8 text-center transition hover:border-skybrand hover:bg-sky-50"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            const file = event.dataTransfer.files.item(0);
            if (file) setSelected(file);
          }}
        >
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            className="sr-only"
            onChange={(event) => setSelected(event.target.files?.item(0) ?? null)}
          />
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-skybrand text-white shadow-glass">
            <FileUp className="h-7 w-7" />
          </div>
          <p className="text-lg font-black text-ink">{selected ? selected.name : "Drop your CSV here"}</p>
          <p className="mt-2 text-sm text-slate-600">CSV or XLSX exports only.</p>
        </label>

        <label className="mt-5 flex gap-3 rounded-xl border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-700">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(event) => setAcknowledged(event.target.checked)}
            className="mt-1 h-4 w-4 rounded border-slate-300"
          />
          <span>
            I confirm that this file does not contain full payment-card numbers, CVV/CVC security codes, passwords,
            authentication secrets, private keys, or other prohibited sensitive credentials.
          </span>
        </label>

        <div className="mt-5 flex flex-col gap-3 sm:flex-row">
          <Button variant="sky" onClick={submit} disabled={!selected || !acknowledged || upload.isPending}>
            {upload.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
            Upload file
          </Button>
          <Button asChild variant="outline"><Link href="/files">View files</Link></Button>
        </div>
      </Card>

      {uploaded ? (
        <Card className="border-green-200 bg-green-50 p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-6 w-6 text-green-600" />
              <div>
                <p className="font-black text-green-900">Upload complete</p>
                <p className="text-sm text-green-700">{uploaded.original_filename}</p>
              </div>
            </div>
            <Button asChild variant="sky"><Link href={`/files/${uploaded.id}/preview`}>Preview file</Link></Button>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
