"use client";

import Image from "next/image";
import { useState, type FormEvent } from "react";

import { Button, ErrorText, Field } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { TwoFactorSetup, User } from "@/lib/types";
import { useSubmit } from "@/lib/use-submit";

/** Turn 2FA on (setup → scan QR → confirm code) or off (password + code). */
export function TwoFactorPanel() {
  const { user, setUser } = useAuth();
  const { error, loading, run } = useSubmit();

  const [setup, setSetup] = useState<TwoFactorSetup | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");

  if (!user) {
    return null;
  }

  function startSetup() {
    run(async () => {
      setSetup(await api<TwoFactorSetup>("/auth/2fa/setup", { method: "POST", auth: true }));
      setCode("");
    });
  }

  function handleEnable(event: FormEvent) {
    event.preventDefault();
    run(async () => {
      setUser(await api<User>("/auth/2fa/enable", { method: "POST", body: { code }, auth: true }));
      setSetup(null);
      setCode("");
    });
  }

  function handleDisable(event: FormEvent) {
    event.preventDefault();
    run(async () => {
      setUser(
        await api<User>("/auth/2fa/disable", {
          method: "POST",
          body: { password, code },
          auth: true,
        }),
      );
      setPassword("");
      setCode("");
    });
  }

  const codeField = (
    <Field
      label="6-digit code from your app"
      value={code}
      onChange={(e) => setCode(e.target.value.trim())}
      inputMode="numeric"
      autoComplete="one-time-code"
      pattern="\d{6}"
      maxLength={6}
      required
    />
  );

  return (
    <section className="rounded-xl border border-neutral-200 p-4 dark:border-neutral-800">
      <h2 className="mb-1 font-semibold">Two-factor authentication</h2>
      <p className="mb-4 text-sm text-neutral-500">
        Status:{" "}
        {user.totp_enabled ? (
          <span className="font-medium text-green-600">On ✓</span>
        ) : (
          <span className="font-medium">Off</span>
        )}
      </p>

      <ErrorText message={error} />

      {user.totp_enabled ? (
        <form onSubmit={handleDisable}>
          <Field
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          {codeField}
          <Button type="submit" variant="secondary" loading={loading}>
            Turn off 2FA
          </Button>
        </form>
      ) : setup ? (
        <form onSubmit={handleEnable}>
          <p className="mb-3 text-sm">
            1. Scan this QR code with Google Authenticator or Microsoft Authenticator:
          </p>
          <Image
            src={setup.qr_code_data_uri}
            alt="QR code for your authenticator app"
            width={180}
            height={180}
            unoptimized
            className="mx-auto mb-3 rounded-lg bg-white p-2"
          />
          <p className="mb-1 text-sm">Can&apos;t scan? Type this key into the app:</p>
          <code className="mb-4 block break-all rounded bg-neutral-100 px-2 py-1 text-xs dark:bg-neutral-900">
            {setup.secret}
          </code>
          <p className="mb-3 text-sm">2. Type the code the app shows:</p>
          {codeField}
          <Button type="submit" loading={loading}>
            Turn on 2FA
          </Button>
        </form>
      ) : (
        <Button onClick={startSetup} loading={loading}>
          Set up 2FA
        </Button>
      )}
    </section>
  );
}
