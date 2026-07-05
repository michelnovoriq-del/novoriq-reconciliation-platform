"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { getToken } from "@/lib/api/client";
import { useAuth } from "@/lib/hooks/use-auth";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const hasToken = typeof window !== "undefined" && Boolean(getToken());

  useEffect(() => {
    if (!hasToken && !isLoading) router.replace("/login");
  }, [hasToken, isLoading, router]);

  if (isLoading || (hasToken && !isAuthenticated)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream">
        <Loader2 className="h-8 w-8 animate-spin text-deepblue" />
      </div>
    );
  }

  return <>{children}</>;
}
