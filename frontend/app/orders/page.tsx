"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/order-status";
import { ErrorText, Loading, Page } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatPrice } from "@/lib/money";
import type { Order } from "@/lib/types";

/** Every order the logged-in user has placed, newest first. */
export default function OrdersPage() {
  const { status } = useAuth();
  const router = useRouter();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Not logged in? Go to the login page.
  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);

  useEffect(() => {
    if (status !== "authenticated") return;
    let cancelled = false; // ignore the answer if this page was closed meanwhile
    api<Order[]>("/orders", { auth: true })
      .then((data) => {
        if (!cancelled) setOrders(data);
      })
      .catch((err) => {
        if (!cancelled) setError(messageFrom(err));
      });
    return () => {
      cancelled = true;
    };
  }, [status]);

  if (status !== "authenticated") {
    return <Loading />;
  }

  return (
    <Page title="My orders">
      <ErrorText message={error} />

      {orders === null ? (
        !error && <p className="text-sm text-neutral-500">Loading…</p>
      ) : orders.length === 0 ? (
        <p className="text-sm text-neutral-500">You haven&apos;t ordered anything yet.</p>
      ) : (
        <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
          {orders.map((order) => {
            const count = order.items.reduce((sum, item) => sum + item.quantity, 0);
            return (
              <li key={order.id}>
                <Link
                  href={`/orders/${order.id}`}
                  className="flex items-center justify-between gap-4 py-4 hover:bg-neutral-50 dark:hover:bg-neutral-900"
                >
                  <div>
                    <p className="font-medium">{new Date(order.created_at).toLocaleString()}</p>
                    <p className="text-sm text-neutral-500">
                      {count} {count === 1 ? "item" : "items"} · Order {order.id.slice(0, 8)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">{formatPrice(order.total_cents)}</p>
                    <StatusBadge status={order.status} />
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      <Link href="/shop" className="mt-6 inline-block text-sm text-blue-600 hover:underline">
        ← Back to the shop
      </Link>
    </Page>
  );
}
