"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, clearToken, getToken, setToken, type User } from "@/lib/api/client";

type AuthContextValue = {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: { email: string; password: string }) => Promise<void>;
  register: (payload: {
    full_name?: string;
    email: string;
    password: string;
    organization_name: string;
  }) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    setHasToken(Boolean(getToken()));
  }, []);

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: api.me,
    enabled: hasToken,
    retry: false,
  });

  useEffect(() => {
    if (meQuery.error) {
      clearToken();
      setHasToken(false);
      queryClient.clear();
    }
  }, [meQuery.error, queryClient]);

  const loginMutation = useMutation({
    mutationFn: api.login,
    onSuccess: async (response) => {
      setToken(response.access_token);
      setHasToken(true);
      await queryClient.invalidateQueries({ queryKey: ["me"] });
      router.push("/dashboard");
    },
  });

  const registerMutation = useMutation({
    mutationFn: api.register,
    onSuccess: async (response) => {
      setToken(response.access_token);
      setHasToken(true);
      if (response.user) queryClient.setQueryData(["me"], response.user);
      router.push("/dashboard");
    },
  });

  const value = useMemo<AuthContextValue>(
    () => ({
      user: meQuery.data ?? null,
      isLoading: hasToken && meQuery.isLoading,
      isAuthenticated: Boolean(meQuery.data),
      login: async (payload) => {
        await loginMutation.mutateAsync(payload);
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
    }),
    [hasToken, loginMutation, meQuery.data, meQuery.isLoading, queryClient, registerMutation, router],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
