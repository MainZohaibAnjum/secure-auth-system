"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/order-status";
import { ErrorText, Loading, Page } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatPrice } from "@/lib/money";
import type { AdminOrder, OrderStatus } from "@/lib/types";
import { useSubmit } from "@/lib/use-submit";

const FILTERS: { label: string; value: OrderStatus | null }[] = [
  { label: "All", value: null },
  { label: "Paid", value: "paid" },
  { label: "Shipped", value: "shipped" },
  { label: "Delivered", value: "delivered" },
  { label: "Cancelled", value: "cancelled" },
];

// The buttons each status gets. Same rules as the server, which checks them again.
const ACTIONS: Record<OrderStatus, { label: string; next: OrderStatus }[]> = {
  paid: [
    { label: "Mark shipped", next: "shipped" },
    { label: "Cancel", next: "cancelled" },
  ],
  shipped: [{ label: "Mark delivered", next: "delivered" }],
  delivered: [],
  cancelled: [],
};

const smallButton =
  "rounded-lg border border-neutral-300 px-2 py-1 text-xs hover:bg-neutral-100 disabled:opacity-40 dark:border-neutral-700 dark:hover:bg-neutral-900";

/** Admins only: every customer's orders, and buttons to move them on. */
export default function AdminOrdersPage() {
  const { status, user } = useAuth();
  const router = useRouter();
  const { error, loading, run } = useSubmit();
  const [orders, setOrders] = useState<AdminOrder[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filter, setFilter] = useState<OrderStatus | null>(null);
  // Bump this number to load the list again
  const [version, setVersion] = useState(0);
  const isAdmin = user?.role === "admin";

  // Not logged in? Go to the login page.
  useEffect(() => {
    if (status === "anonymous") router.replace("/admin/login");
  }, [status, router]);

  useEffect(() => {
    if (!isAdmin) return;
    let cancelled = false; // ignore the answer if this page was closed meanwhile
    const query = filter ? `?status=${filter}` : "";
    api<AdminOrder[]>(`/admin/orders${query}`, { auth: true })
      .then((data) => {
        if (!cancelled) {
          setOrders(data);
          setLoadError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setLoadError(messageFrom(err));
      });
    return () => {
      cancelled = true;
    };
  }, [isAdmin, filter, version]);

  if (status !== "authenticated" || !user) {
    return <Loading />;
  }

  function changeStatus(order: AdminOrder, next: OrderStatus) {
    if (next === "cancelled" && !window.confirm("Cancel this order? The items go back in stock.")) {
      return;
    }
    run(async () => {
      try {
        await api(`/admin/orders/${order.id}`, {
          method: "PATCH",
          body: { status: next },
          auth: true,
        });
      } finally {
        // Reload even if it failed: someone else may have just changed this order
        setVersion((v) => v + 1);
      }
    });
  }

  return (
    <Page title="Orders">
      {!isAdmin ? (
        <ErrorText message="Admins only." />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap gap-2">
            {FILTERS.map((f) => (
              <button
                key={f.label}
                onClick={() => setFilter(f.value)}
                className={`rounded-full px-3 py-1 text-sm ${
                  filter === f.value
                    ? "bg-blue-600 text-white"
                    : "border border-neutral-300 hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <ErrorText message={loadError ?? error} />

          {orders === null ? (
            !loadError && <p className="text-sm text-neutral-500">Loading…</p>
          ) : orders.length === 0 ? (
            <p className="text-sm text-neutral-500">No orders here.</p>
          ) : (
            <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
              {orders.map((order) => (
                <li key={order.id} className="py-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{order.user_email}</p>
                      <p className="text-sm text-neutral-500">
                        Order {order.id.slice(0, 8)} · {new Date(order.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{formatPrice(order.total_cents)}</p>
                      <StatusBadge status={order.status} />
                    </div>
                  </div>

                  <ul className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                    {order.items.map((item, index) => (
                      <li key={index}>
                        {item.quantity} × {item.product_name}
                      </li>
                    ))}
                  </ul>

                  {ACTIONS[order.status].length > 0 && (
                    <div className="mt-2 flex gap-2">
                      {ACTIONS[order.status].map((action) => (
                        <button
                          key={action.next}
                          className={smallButton}
                          disabled={loading}
                          onClick={() => changeStatus(order, action.next)}
                        >
                          {action.label}
                        </button>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      <Link href="/admin" className="mt-6 inline-block text-sm text-blue-600 hover:underline">
        ← Back to admin
      </Link>
    </Page>
  );
}
