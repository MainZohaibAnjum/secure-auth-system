"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Card, ErrorText, Loading } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { AdminUser } from "@/lib/types";

/** Admins only: every account. Hiding this page isn't the protection; the server checks the role. */
export default function AdminPage() {
  const { status, user } = useAuth();
  const router = useRouter();
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const isAdmin = user?.role === "admin";

  // Not logged in? Go to the login page.
  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);

  useEffect(() => {
    if (!isAdmin) return;
    let cancelled = false; // ignore the answer if this page was closed meanwhile
    api<AdminUser[]>("/admin/users", { auth: true })
      .then((data) => {
        if (!cancelled) setUsers(data);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(messageFrom(err));
      });
    return () => {
      cancelled = true;
    };
  }, [isAdmin]);

  if (status !== "authenticated" || !user) {
    return <Loading />;
  }

  return (
    <Card title="All users">
      {!isAdmin ? (
        <ErrorText message="Admins only." />
      ) : (
        <>
          <ErrorText message={loadError} />
          {users === null ? (
            <p className="text-sm text-neutral-500">{loadError ? "" : "Loading…"}</p>
          ) : (
            <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
              {users.map((u) => (
                <li key={u.id} className="py-3 text-sm">
                  <p className="truncate font-medium">{u.email}</p>
                  <p className="text-neutral-500">
                    {u.role === "admin" ? <span className="text-blue-600">Admin</span> : "User"}
                    {" · "}
                    {u.totp_enabled ? "2FA on" : "2FA off"}
                    {!u.is_active && <span className="text-red-600"> · Disabled</span>}
                    {" · joined "}
                    {new Date(u.created_at).toLocaleDateString()}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      <Link href="/dashboard" className="mt-4 inline-block text-sm text-blue-600 hover:underline">
        ← Back to dashboard
      </Link>
    </Card>
  );
}
