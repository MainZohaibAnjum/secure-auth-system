"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Button, ErrorText, Field } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import { useSubmit } from "@/lib/use-submit";

/**
 * Email + password, then the 2FA code if the account has 2FA on.
 *
 * admin = true is the "Admin login" page: after logging in, admins go to the
 * admin pages, and customer accounts are logged out again with a message.
 * This is only for convenience. The real protection is on the server, which
 * refuses every /admin request from a non-admin.
 */
export function LoginForm({ admin = false }: { admin?: boolean }) {
  const { status, user, login, verify2fa, logout } = useAuth();
  const router = useRouter();
  const { error, loading, run } = useSubmit();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // Set after a correct password when the account has 2FA on
  const [challengeToken, setChallengeToken] = useState<string | null>(null);
  const [code, setCode] = useState("");
  // Lost phone: type a saved recovery code instead of the app's 6-digit code
  const [recoveryMode, setRecoveryMode] = useState(false);
  const [roleError, setRoleError] = useState<string | null>(null);
  // True once this form has logged someone in (not when they were logged in already)
  const loggedInHere = useRef(false);
  const rejecting = useRef(false);

  // Logged in? Send them to the right place.
  useEffect(() => {
    if (status !== "authenticated" || !user) return;
    if (admin && user.role !== "admin") {
      if (rejecting.current) return; // already logging them out
      if (loggedInHere.current) {
        // A customer account used the admin login: undo it and explain
        rejecting.current = true;
        logout().then(() => {
          rejecting.current = false;
          loggedInHere.current = false;
          setRoleError("This is not an admin account. Customers, please use the normal login.");
          setChallengeToken(null);
        });
      } else {
        router.replace("/dashboard"); // was already logged in as a customer
      }
      return;
    }
    router.replace(admin ? "/admin/orders" : "/dashboard");
  }, [status, user, admin, router, logout]);

  function handlePassword(event: FormEvent) {
    event.preventDefault();
    setRoleError(null);
    run(async () => {
      loggedInHere.current = true;
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

  function toggleRecoveryMode() {
    setRecoveryMode(!recoveryMode);
    setCode("");
  }

  if (challengeToken) {
    return (
      <>
        <h2 className="mb-2 text-xl font-semibold">
          {recoveryMode ? "Use a recovery code" : "Enter your code"}
        </h2>
        <p className="mb-4 text-sm text-neutral-500">
          {recoveryMode
            ? "Type one of the recovery codes you saved when you turned on 2FA. Each code works once."
            : "Open your authenticator app and type the 6-digit code for this account."}
        </p>
        <ErrorText message={error} />
        <form onSubmit={handleCode}>
          <Field
            label={recoveryMode ? "Recovery code" : "6-digit code"}
            value={code}
            onChange={(e) => setCode(e.target.value.trim())}
            inputMode={recoveryMode ? "text" : "numeric"}
            autoComplete={recoveryMode ? "off" : "one-time-code"}
            pattern={recoveryMode ? undefined : "\\d{6}"}
            maxLength={recoveryMode ? 32 : 6}
            required
            autoFocus
          />
          <Button type="submit" loading={loading}>
            Verify
          </Button>
        </form>
        <button
          type="button"
          onClick={toggleRecoveryMode}
          className="mt-4 block text-sm text-blue-600 hover:underline"
        >
          {recoveryMode ? "Use the code from my app instead" : "Lost your phone? Use a recovery code"}
        </button>
        <button
          type="button"
          onClick={() => setChallengeToken(null)}
          className="mt-2 block text-sm text-blue-600 hover:underline"
        >
          ← Back to login
        </button>
      </>
    );
  }

  return (
    <>
      <ErrorText message={roleError ?? error} />
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
          {admin ? "Log in as admin" : "Log in"}
        </Button>
      </form>
    </>
  );
}
