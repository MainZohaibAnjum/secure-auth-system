"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

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
          <dt className="text-neutral-500">Member since</dt>
          <dd className="font-medium">{new Date(user.created_at).toLocaleDateString()}</dd>
        </div>
      </dl>

      <TwoFactorPanel />

      <div className="mt-6">
        <Button variant="secondary" onClick={() => logout()}>
          Log out
        </Button>
      </div>
    </Card>
  );
}
