import { cn } from "@/lib/utils";

const tones = {
  sky: "bg-sky-100 text-deepblue",
  green: "bg-green-100 text-green-700",
  amber: "bg-amber-100 text-amber-700",
  red: "bg-red-100 text-red-700",
  purple: "bg-violet-100 text-violet-700",
  slate: "bg-slate-100 text-slate-700",
};

export function Badge({
  className,
  tone = "slate",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof tones }) {
  return (
    <span
      className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold", tones[tone], className)}
      {...props}
    />
  );
}

export function StatusBadge({ status }: { status?: string }) {
  const normalized = status?.toLowerCase() ?? "unknown";
  const tone =
    ["normalized", "matched", "approved", "completed"].includes(normalized)
      ? "green"
      : ["failed", "failed_normalization", "rejected", "unmatched_file_a", "unmatched_file_b"].includes(normalized)
        ? "red"
        : ["possible_match", "normalized_with_rejections"].includes(normalized)
          ? "amber"
        : normalized === "previewed"
          ? "purple"
          : normalized === "uploaded"
            ? "sky"
            : "slate";
  return <Badge tone={tone}>{normalized}</Badge>;
}
