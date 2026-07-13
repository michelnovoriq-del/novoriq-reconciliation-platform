"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, clearToken, getToken, setToken, type AccountBootstrap, type User } from "@/lib/api/client";

export function safeReturnTo(value?: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) return "/dashboard";
  try {
    const parsed = new URL(value, "http://novoriq.local");
    return parsed.origin === "http://novoriq.local" ? `${parsed.pathname}${parsed.search}${parsed.hash}` : "/dashboard";
  } catch { return "/dashboard"; }
}

type AuthContextValue = {
  user: User | null;
  account: AccountBootstrap | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: { email: string; password: string }, redirectTo?: string) => Promise<void>;
  register: (payload: {
    full_name?: string;
    email: string;
    password: string;
    organization_name: string;
  }) => Promise<void>;
  logout: () => void;
  refreshAccount: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    setHasToken(Boolean(getToken()));
  }, []);

  const accountQuery = useQuery({
    queryKey: ["account", "bootstrap"],
    queryFn: api.getAccountBootstrap,
    enabled: hasToken,
    retry: false,
  });

  useEffect(() => {
    if (accountQuery.error) {
      clearToken();
      setHasToken(false);
      queryClient.clear();
    }
  }, [accountQuery.error, queryClient]);

  const loginMutation = useMutation({
    mutationFn: (payload: { email: string; password: string; redirectTo?: string }) => api.login(payload),
    onSuccess: async (response, variables) => {
      setToken(response.access_token);
      setHasToken(true);
      await queryClient.invalidateQueries({ queryKey: ["account", "bootstrap"] });
      router.push(safeReturnTo(variables.redirectTo));
    },
  });

  const registerMutation = useMutation({
    mutationFn: api.register,
    onSuccess: async (response) => {
      setToken(response.access_token);
      setHasToken(true);
      await queryClient.invalidateQueries({ queryKey: ["account", "bootstrap"] });
      router.push("/onboarding");
    },
  });

  const value = useMemo<AuthContextValue>(
    () => ({
      user: accountQuery.data ? { id: accountQuery.data.user.id, email: accountQuery.data.user.email,
        full_name: accountQuery.data.user.full_name, is_active: true,
        email_verified_at: accountQuery.data.user.email_verified ? new Date().toISOString() : null,
        created_at: "", updated_at: "" } : null,
      account: accountQuery.data ?? null,
      isLoading: hasToken && accountQuery.isLoading,
      isAuthenticated: Boolean(accountQuery.data),
      login: async (payload, redirectTo) => {
        await loginMutation.mutateAsync({ ...payload, redirectTo });
      },
      register: async (payload) => {
        await registerMutation.mutateAsync(payload);
      },
      logout: () => {
        clearToken();
        setHasToken(false);
        queryClient.clear();
        router.push("/login");
      },
      refreshAccount: async () => { await accountQuery.refetch(); },
    }),
    [accountQuery, hasToken, loginMutation, queryClient, registerMutation, router],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
