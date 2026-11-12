"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { RecoveryCodesPanel } from "@/components/recovery-codes";
import { SessionsPanel } from "@/components/sessions-panel";
import { TwoFactorPanel } from "@/components/two-factor-panel";
import { Button, Card, Loading } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";

export default function DashboardPage() {
  const { status, user, logout } = useAuth();
  const router = useRouter();

  // Not logged in? Go to the login page.
  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);

  if (status !== "authenticated" || !user) {
    return <Loading />;
  }

  return (
    <Card title="Dashboard">
      <dl className="mb-6 space-y-2 text-sm">
        <div>
          <dt className="text-neutral-500">Email</dt>
          <dd className="font-medium">{user.email}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">Role</dt>
          <dd className="font-medium">{user.role === "admin" ? "Admin" : "User"}</dd>
        </div>
        <div>
          <dt className="text-neutral-500">Member since</dt>
          <dd className="font-medium">{new Date(user.created_at).toLocaleDateString()}</dd>
        </div>
      </dl>
      <Link href="/shop" className="mb-2 block text-sm text-blue-600 hover:underline">
        Go to the shop →
      </Link>

      {/* Only a shortcut: the server itself refuses /admin requests from non-admins */}
      {user.role === "admin" && (
        <Link href="/admin" className="mb-6 block text-sm text-blue-600 hover:underline">
          Admin: see all users →
        </Link>
      )}

      <TwoFactorPanel />
      <RecoveryCodesPanel />
      <SessionsPanel />

      <div className="mt-6">
        <Button variant="secondary" onClick={() => logout()}>
          Log out
        </Button>
      </div>
    </Card>
  );
}
