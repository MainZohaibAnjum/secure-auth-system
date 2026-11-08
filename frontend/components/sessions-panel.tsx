"use client";

import { useEffect, useState } from "react";

import { Button, ErrorText } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { describeDevice, timeAgo } from "@/lib/devices";
import type { DeviceSession } from "@/lib/types";
import { useSubmit } from "@/lib/use-submit";

/** Every device where this account is logged in, with buttons to log them out. */
export function SessionsPanel() {
  const { error, loading, run } = useSubmit();
  const [sessions, setSessions] = useState<DeviceSession[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  // Bump this number to load the list again
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false; // ignore the answer if this panel was closed meanwhile
    api<DeviceSession[]>("/auth/sessions", { auth: true })
      .then((data) => {
        if (!cancelled) setSessions(data);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(messageFrom(err));
      });
    return () => {
      cancelled = true;
    };
  }, [version]);

  function revoke(id: string) {
    run(async () => {
      await api(`/auth/sessions/${id}/revoke`, { method: "POST", auth: true });
      setVersion((v) => v + 1);
    });
  }

  function revokeOthers() {
    run(async () => {
      await api("/auth/sessions/revoke-others", { method: "POST", auth: true });
      setVersion((v) => v + 1);
    });
  }

  return (
    <section className="mt-6 rounded-xl border border-neutral-200 p-4 dark:border-neutral-800">
      <h2 className="mb-1 font-semibold">Your devices</h2>
      <p className="mb-3 text-sm text-neutral-500">Where your account is logged in right now.</p>

      <ErrorText message={error ?? loadError} />

      {sessions === null ? (
        <p className="text-sm text-neutral-500">Loading…</p>
      ) : (
        <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
          {sessions.map((session) => (
            <li key={session.id} className="flex items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="text-sm font-medium">
                  {describeDevice(session.user_agent)}
                  {session.current && (
                    <span className="ml-2 rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700 dark:bg-green-950 dark:text-green-300">
                      This device
                    </span>
                  )}
                </p>
                <p className="text-xs text-neutral-500">
                  {session.ip ?? "Unknown IP"} · active {timeAgo(session.last_active_at)}
                </p>
              </div>
              {!session.current && (
                <button
                  type="button"
                  onClick={() => revoke(session.id)}
                  disabled={loading}
                  className="shrink-0 text-sm text-red-600 hover:underline disabled:opacity-50"
                >
                  Log out
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {sessions && sessions.length > 1 && (
        <div className="mt-4">
          <Button variant="secondary" onClick={revokeOthers} loading={loading}>
            Log out all other devices
          </Button>
        </div>
      )}
    </section>
  );
}
