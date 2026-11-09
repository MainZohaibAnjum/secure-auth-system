"use client";

import { useEffect, useState, type FormEvent } from "react";

import { Button, ErrorText, Field } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { RecoveryCodes, RecoveryCodesStatus } from "@/lib/types";
import { useSubmit } from "@/lib/use-submit";

/** Freshly made recovery codes. The server never shows them again, so the user must save them now. */
export function RecoveryCodesList({ codes, onDone }: { codes: string[]; onDone: () => void }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(codes.join("\n"));
    setCopied(true);
  }

  return (
    <div>
      <p className="mb-1 text-sm font-medium">Save your recovery codes</p>
      <p className="mb-3 text-sm text-neutral-500">
        If you lose your phone, each code lets you log in once. You won&apos;t see them again.
      </p>
      <ul className="mb-3 space-y-1 rounded bg-neutral-100 p-3 text-center font-mono text-sm dark:bg-neutral-900">
        {codes.map((code) => (
          <li key={code}>{code}</li>
        ))}
      </ul>
      <div className="mb-2">
        <Button variant="secondary" onClick={copy}>
          {copied ? "Copied ✓" : "Copy codes"}
        </Button>
      </div>
      <Button onClick={onDone}>I&apos;ve saved them</Button>
    </div>
  );
}

/** How many recovery codes are left, and a way to make a new set. Only shown when 2FA is on. */
export function RecoveryCodesPanel() {
  const { user } = useAuth();
  const { error, loading, run } = useSubmit();
  const [remaining, setRemaining] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [newCodes, setNewCodes] = useState<string[] | null>(null);
  const enabled = user?.totp_enabled ?? false;

  // Load the count when 2FA is on, and again after the user has saved new codes
  useEffect(() => {
    if (!enabled || newCodes) return;
    let cancelled = false; // ignore the answer if this panel was closed meanwhile
    api<RecoveryCodesStatus>("/auth/2fa/recovery-codes", { auth: true })
      .then((data) => {
        if (!cancelled) setRemaining(data.remaining);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(messageFrom(err));
      });
    return () => {
      cancelled = true;
    };
  }, [enabled, newCodes]);

  if (!enabled) {
    return null;
  }

  function handleRegenerate(event: FormEvent) {
    event.preventDefault();
    run(async () => {
      const result = await api<RecoveryCodes>("/auth/2fa/recovery-codes", {
        method: "POST",
        body: { password, code },
        auth: true,
      });
      setNewCodes(result.recovery_codes);
      setShowForm(false);
      setPassword("");
      setCode("");
    });
  }

  return (
    <section className="mt-6 rounded-xl border border-neutral-200 p-4 dark:border-neutral-800">
      <h2 className="mb-1 font-semibold">Recovery codes</h2>

      {newCodes ? (
        <RecoveryCodesList codes={newCodes} onDone={() => setNewCodes(null)} />
      ) : (
        <>
          <p className="mb-3 text-sm text-neutral-500">
            {remaining === null ? "Loading…" : `${remaining} unused ${remaining === 1 ? "code" : "codes"} left.`}
            {remaining !== null && remaining <= 3 && (
              <span className="text-amber-600"> Make new ones soon.</span>
            )}
          </p>

          <ErrorText message={error ?? loadError} />

          {showForm ? (
            <form onSubmit={handleRegenerate}>
              <Field
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
              <Field
                label="6-digit code (or a recovery code)"
                value={code}
                onChange={(e) => setCode(e.target.value.trim())}
                autoComplete="one-time-code"
                maxLength={32}
                required
              />
              <Button type="submit" loading={loading}>
                Make new codes
              </Button>
            </form>
          ) : (
            <Button variant="secondary" onClick={() => setShowForm(true)}>
              Get new codes
            </Button>
          )}
        </>
      )}
    </section>
  );
}
