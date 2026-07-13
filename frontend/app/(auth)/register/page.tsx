"use client";

import Link from "next/link";
import { useState } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { AuthCard } from "@/components/layout/auth-card";
import { ErrorAlert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/hooks/use-auth";

const schema = z.object({
  full_name: z.string().min(2, "Enter your name."),
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(8, "Use at least 8 characters."),
  confirm_password: z.string(),
  organization_name: z.string().min(1, "Organization name is required."),
  terms: z.literal(true, { errorMap: () => ({ message: "You must accept the Terms and Privacy Policy." }) }),
}).refine((values) => values.password === values.confirm_password, {
  path: ["confirm_password"], message: "Passwords do not match.",
});

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register } = useAuth();
  const [error, setError] = useState("");
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", email: "", password: "", confirm_password: "", organization_name: "", terms: false as true },
  });

  async function onSubmit(values: FormValues) {
    setError("");
    try {
      await register({ full_name: values.full_name, email: values.email, password: values.password,
        organization_name: values.organization_name });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create account.");
    }
  }

  return (
    <AuthCard
      title="Create your workspace"
      description="Start the controlled CSV reconciliation workflow for your team."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="font-bold text-deepblue hover:underline">
            Login
          </Link>
        </>
      }
    >
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <ErrorAlert message={error} />
        <div className="space-y-2">
          <Label htmlFor="full_name">Full name</Label>
          <Input id="full_name" autoComplete="name" {...form.register("full_name")} />
          <p className="text-xs text-red-600">{form.formState.errors.full_name?.message}</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="confirm_password">Confirm password</Label>
          <Input id="confirm_password" type="password" autoComplete="new-password" {...form.register("confirm_password")} />
          <p className="text-xs text-red-600">{form.formState.errors.confirm_password?.message}</p>
        </div>
        <label className="flex items-start gap-3 text-sm text-slate-700">
          <input type="checkbox" className="mt-1 h-4 w-4" {...form.register("terms")} />
          <span>I agree to the <Link className="font-bold text-deepblue underline" href="/terms">Terms of Service</Link> and acknowledge the <Link className="font-bold text-deepblue underline" href="/privacy">Privacy Policy</Link>.</span>
        </label>
        <p className="text-xs text-red-600">{form.formState.errors.terms?.message}</p>
        <div className="space-y-2">
          <Label htmlFor="organization_name">Organization</Label>
          <Input id="organization_name" autoComplete="organization" {...form.register("organization_name")} />
          <p className="text-xs text-red-600">{form.formState.errors.organization_name?.message}</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
          <p className="text-xs text-red-600">{form.formState.errors.email?.message}</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" autoComplete="new-password" {...form.register("password")} />
          <p className="text-xs text-red-600">{form.formState.errors.password?.message}</p>
        </div>
        <Button type="submit" variant="sky" className="w-full" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {form.formState.isSubmitting ? "Creating your Novoriq workspace..." : "Create account"}
        </Button>
      </form>
    </AuthCard>
  );
}
