import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export function ErrorAlert({ message, className }: { message?: string; className?: string }) {
  if (!message) return null;
  return (
    <div className={cn("flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700", className)}>
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <p>{message}</p>
    </div>
  );
}
