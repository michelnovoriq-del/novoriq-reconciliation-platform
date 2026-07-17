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

const schema = z.object({
  full_name: z.string().trim().min(1, "Full name is required."),
  organization_name: z.string().trim().min(1, "Organization name is required."),
  email: z.string().trim().min(1, "Work email is required.").email("Enter a valid email address."),
  password: z.string().min(8, "Use at least 8 characters."),
  confirm_password: z.string().min(1, "Confirm your password."),
  terms: z.boolean().refine((accepted) => accepted, "You must accept the Terms and Privacy Policy."),
}).refine((values) => values.password === values.confirm_password, { path: ["confirm_password"], message: "Passwords do not match." });

type FormValues = z.infer<typeof schema>;
type FieldName = Exclude<keyof FormValues, "terms">;

function Field({ name, label, type = "text", autoComplete, form, toggle, describedBy }: {
  name: FieldName; label: string; type?: string; autoComplete: string; form: ReturnType<typeof useForm<FormValues>>;
  toggle?: React.ReactNode; describedBy?: string;
}) {
  const error = form.formState.errors[name]?.message;
  const errorId = `${name}-error`;
  return <div className="space-y-2">
    <Label htmlFor={name}>{label}</Label>
    <div className="relative"><Input id={name} type={type} autoComplete={autoComplete} aria-invalid={Boolean(error)} aria-describedby={[describedBy, error ? errorId : ""].filter(Boolean).join(" ") || undefined} className={toggle ? "pr-12" : undefined} {...form.register(name)} />{toggle}</div>
    {error && <p id={errorId} role="alert" className="text-xs font-medium text-red-700">{error}</p>}
  </div>;
}

export default function RegisterPage() {
  const { register } = useAuth();
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const form = useForm<FormValues>({ resolver: zodResolver(schema), shouldFocusError: true, defaultValues: { full_name: "", organization_name: "", email: "", password: "", confirm_password: "", terms: false } });
  const toggle = (shown: boolean, setShown: (value: boolean) => void, label: string) => <button type="button" onClick={() => setShown(!shown)} aria-label={`${shown ? "Hide" : "Show"} ${label}`} className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-xl text-slate-500 hover:text-deepblue focus-visible:outline focus-visible:outline-2 focus-visible:outline-skybrand">{shown ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>;

  async function onSubmit(values: FormValues) {
    if (form.formState.isSubmitting) return;
    setError("");
    try { await register({ full_name: values.full_name, email: values.email, password: values.password, organization_name: values.organization_name }); }
    catch (err) { setError(err instanceof Error ? err.message : "Something went wrong while creating your workspace. Please try again."); }
  }

  return <AuthCard mode="register" title="Create your workspace" description="Start your Free Forever reconciliation workspace." footer={<>Already have an account? <Link href="/login" className="font-bold text-deepblue hover:underline">Login</Link></>}>
    <form onSubmit={form.handleSubmit(onSubmit, (errors) => { const first = ["full_name", "organization_name", "email", "password", "confirm_password", "terms"].find((name) => errors[name as keyof FormValues]); if (first) window.setTimeout(() => form.setFocus(first as keyof FormValues), 0); })} noValidate className="space-y-5" aria-busy={form.formState.isSubmitting}>
      <ErrorAlert message={error} />
      <Field name="full_name" label="Full name" autoComplete="name" form={form} />
      <Field name="organization_name" label="Organization name" autoComplete="organization" form={form} />
      <Field name="email" label="Work email" type="email" autoComplete="email" form={form} />
      <div className="grid gap-5 sm:grid-cols-2">
        <div><Field name="password" label="Password" type={showPassword ? "text" : "password"} autoComplete="new-password" form={form} describedBy="password-help" toggle={toggle(showPassword, setShowPassword, "password")} /><p id="password-help" className="mt-2 text-xs text-slate-500">Use at least the minimum password length required by Novoriq.</p></div>
        <Field name="confirm_password" label="Confirm password" type={showConfirmation ? "text" : "password"} autoComplete="new-password" form={form} toggle={toggle(showConfirmation, setShowConfirmation, "password confirmation")} />
      </div>
      <div><label className="flex items-start gap-3 text-sm leading-6 text-slate-700"><input type="checkbox" className="mt-1 h-4 w-4 shrink-0 accent-skybrand focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-skybrand" aria-invalid={Boolean(form.formState.errors.terms)} aria-describedby={form.formState.errors.terms ? "terms-error" : undefined} {...form.register("terms")} /><span>I agree to the <Link className="font-bold text-deepblue underline" href="/terms">Terms of Service</Link> and acknowledge the <Link className="font-bold text-deepblue underline" href="/privacy">Privacy Policy</Link>.</span></label>{form.formState.errors.terms && <p id="terms-error" role="alert" className="mt-2 text-xs font-medium text-red-700">{form.formState.errors.terms.message}</p>}</div>
      <Button type="submit" variant="sky" className="w-full" disabled={form.formState.isSubmitting} aria-live="polite">{form.formState.isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}{form.formState.isSubmitting ? "Creating your workspace..." : "Create Free Workspace"}</Button>
    </form>
  </AuthCard>;
}
