"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Button, Card, ErrorText, Field } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import { useSubmit } from "@/lib/use-submit";

export default function LoginPage() {
  const { status, login, verify2fa } = useAuth();
  const router = useRouter();
  const { error, loading, run } = useSubmit();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // Set after a correct password when the account has 2FA on
  const [challengeToken, setChallengeToken] = useState<string | null>(null);
  const [code, setCode] = useState("");

  // Logged in (just now, or from before)? Go to the dashboard.
  useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard");
  }, [status, router]);

  function handlePassword(event: FormEvent) {
    event.preventDefault();
    run(async () => {
      const result = await login(email, password);
      if (result.requires2fa) {
        setChallengeToken(result.challengeToken);
      }
    });
  }

  function handleCode(event: FormEvent) {
    event.preventDefault();
    run(() => verify2fa(challengeToken!, code));
  }

  if (challengeToken) {
    return (
      <Card title="Enter your code">
        <p className="mb-4 text-sm text-neutral-500">
          Open your authenticator app and type the 6-digit code for this account.
        </p>
        <ErrorText message={error} />
        <form onSubmit={handleCode}>
          <Field
            label="6-digit code"
            value={code}
            onChange={(e) => setCode(e.target.value.trim())}
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="\d{6}"
            maxLength={6}
            required
            autoFocus
          />
          <Button type="submit" loading={loading}>
            Verify
          </Button>
        </form>
        <button
          type="button"
          onClick={() => setChallengeToken(null)}
          className="mt-4 text-sm text-blue-600 hover:underline"
        >
          ← Back to login
        </button>
      </Card>
    );
  }

  return (
    <Card title="Log in">
      <ErrorText message={error} />
      <form onSubmit={handlePassword}>
        <Field
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          required
        />
        <Field
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
        <Button type="submit" loading={loading}>
          Log in
        </Button>
      </form>
      <p className="mt-4 text-sm text-neutral-500">
        No account?{" "}
        <Link href="/signup" className="text-blue-600 hover:underline">
          Sign up
        </Link>
      </p>
    </Card>
  );
}
