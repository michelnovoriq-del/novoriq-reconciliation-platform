"use client";

import Link from "next/link";
import { useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { AuthCard } from "@/components/layout/auth-card";
import { ErrorAlert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/hooks/use-auth";

const schema = z.object({ email: z.string().trim().min(1, "Work email is required.").email("Enter a valid email address."), password: z.string().min(1, "Password is required.") });
type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const { login } = useAuth();
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const form = useForm<FormValues>({ resolver: zodResolver(schema), shouldFocusError: true, defaultValues: { email: "", password: "" } });

  async function onSubmit(values: FormValues) {
    if (form.formState.isSubmitting) return;
    setError("");
    try {
      const returnTo = typeof window === "undefined" ? undefined : new URLSearchParams(window.location.search).get("returnTo") ?? undefined;
      await login(values, returnTo);
    } catch (err) { setError(err instanceof Error ? err.message : "Email or password is incorrect."); }
  }

  const emailError = form.formState.errors.email?.message;
  const passwordError = form.formState.errors.password?.message;
  return <AuthCard mode="login" title="Welcome back" description="Sign in to continue your reconciliation workflow." footer={<>New to Novoriq? <Link href="/register" className="font-bold text-deepblue hover:underline">Create a Free Forever workspace.</Link></>}>
    <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-5" aria-busy={form.formState.isSubmitting}>
      <ErrorAlert message={error} />
      <div className="space-y-2"><Label htmlFor="email">Work email</Label><Input id="email" type="email" autoComplete="email" aria-invalid={Boolean(emailError)} aria-describedby={emailError ? "email-error" : undefined} {...form.register("email")} />{emailError && <p id="email-error" role="alert" className="text-xs font-medium text-red-700">{emailError}</p>}</div>
      <div className="space-y-2"><Label htmlFor="password">Password</Label><div className="relative"><Input id="password" type={showPassword ? "text" : "password"} autoComplete="current-password" aria-invalid={Boolean(passwordError)} aria-describedby={passwordError ? "password-error" : undefined} className="pr-12" {...form.register("password")} /><button type="button" onClick={() => setShowPassword(!showPassword)} aria-label={`${showPassword ? "Hide" : "Show"} password`} className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-xl text-slate-500 hover:text-deepblue focus-visible:outline focus-visible:outline-2 focus-visible:outline-skybrand">{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div>{passwordError && <p id="password-error" role="alert" className="text-xs font-medium text-red-700">{passwordError}</p>}</div>
      <Button type="submit" variant="sky" className="w-full" disabled={form.formState.isSubmitting} aria-live="polite">{form.formState.isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}{form.formState.isSubmitting ? "Signing in..." : "Sign In"}</Button>
    </form>
  </AuthCard>;
}
