"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/Alert";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

/** Where each role lands right after signing in. */
function landingPathForRole(role?: string): string {
  if (role === "admin") return "/dashboard";
  if (role === "agent") return "/tickets/queue";
  return "/tickets";
}

export default function LoginPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setIsSubmitting(true);

    try {
      await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      const me = await refreshUser();
      router.push(landingPathForRole(me?.role));
      router.refresh();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Could not connect to the server."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <div className="rounded-lg border border-border bg-surface p-6 shadow-sm">
        <h1 className="text-2xl font-bold">Login to DeskLite</h1>
        <p className="mt-2 text-sm text-muted">
          Access your internal support tickets.
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit} noValidate>
          <Input
            id="email"
            label="Email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            required
          />

          <Input
            id="password"
            label="Password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
            required
          />

          {message && <Alert variant="error">{message}</Alert>}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Sign in"}
          </Button>
        </form>

        <p className="mt-4 text-sm text-muted">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="text-brand underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
