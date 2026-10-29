"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Button, Card, ErrorText, Field } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import { useSubmit } from "@/lib/use-submit";

export default function SignupPage() {
  const { status, signup, login } = useAuth();
  const router = useRouter();
  const { error, loading, run } = useSubmit();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");

  useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard");
  }, [status, router]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    run(async () => {
      if (password !== confirm) {
        throw new Error("Passwords don't match");
      }
      await signup(email, password);
      await login(email, password); // a new account has no 2FA yet, so this logs straight in
    });
  }

  return (
    <Card title="Create account">
      <ErrorText message={error} />
      <form onSubmit={handleSubmit}>
        <Field
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          required
        />
        <Field
          label="Password (at least 12 characters)"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
          minLength={12}
          maxLength={128}
          required
        />
        <Field
          label="Confirm password"
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          autoComplete="new-password"
          required
        />
        <Button type="submit" loading={loading}>
          Sign up
        </Button>
      </form>
      <p className="mt-4 text-sm text-neutral-500">
        Already have an account?{" "}
        <Link href="/login" className="text-blue-600 hover:underline">
          Log in
        </Link>
      </p>
    </Card>
  );
}
