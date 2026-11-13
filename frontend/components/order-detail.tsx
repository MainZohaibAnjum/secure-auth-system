"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/order-status";
import { Button, ErrorText, Loading, Page } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatPrice } from "@/lib/money";
import type { Order } from "@/lib/types";
import { useSubmit } from "@/lib/use-submit";

/** One of the user's orders: what they bought and what they paid. */
export function OrderDetail() {
  const { id } = useParams<{ id: string }>();
  // The cart page adds ?new=1 right after checkout, to say thank you
  const isNew = useSearchParams().get("new") === "1";
  const { status } = useAuth();
  const router = useRouter();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const cancel = useSubmit();

  // Not logged in? Go to the login page.
  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);

  useEffect(() => {
    if (status !== "authenticated") return;
    let cancelled = false; // ignore the answer if this page was closed meanwhile
    api<Order>(`/orders/${encodeURIComponent(id)}`, { auth: true })
      .then((data) => {
        if (!cancelled) setOrder(data);
      })
      .catch((err) => {
        if (!cancelled) setError(messageFrom(err));
      });
    return () => {
      cancelled = true;
    };
  }, [status, id]);

  if (status !== "authenticated") {
    return <Loading />;
  }

  function cancelOrder() {
    if (!window.confirm("Cancel this order?")) return;
    cancel.run(async () => {
      const url = `/orders/${encodeURIComponent(id)}/cancel`;
      setOrder(await api<Order>(url, { method: "POST", auth: true }));
    });
  }

  return (
    <Page title="Order">
      <ErrorText message={error} />

      {order ? (
        <>
          {isNew && order.status === "paid" && (
            <p className="mb-4 rounded-lg bg-green-50 px-3 py-2 text-sm text-green-700 dark:bg-green-950 dark:text-green-300">
              Thank you! Your order has been placed.
            </p>
          )}

          <p className="mb-4 text-sm text-neutral-500">
            Order {order.id.slice(0, 8)} · {new Date(order.created_at).toLocaleString()} ·{" "}
            <StatusBadge status={order.status} />
          </p>

          <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
            {order.items.map((item, index) => (
              <li key={index} className="flex items-center justify-between gap-4 py-3">
                <div className="min-w-0">
                  {/* Link to the product only if it still exists */}
                  {item.product_id ? (
                    <Link href={`/shop/${item.product_id}`} className="font-medium hover:underline">
                      {item.product_name}
                    </Link>
                  ) : (
                    <span className="font-medium">{item.product_name}</span>
                  )}
                  <p className="text-sm text-neutral-500">
                    {item.quantity} × {formatPrice(item.unit_price_cents)}
                  </p>
                </div>
                <p className="font-medium">{formatPrice(item.line_total_cents)}</p>
              </li>
            ))}
          </ul>

          <div className="mt-4 flex items-center justify-between border-t border-neutral-200 pt-4 text-lg font-semibold dark:border-neutral-800">
            <span>Total</span>
            <span>{formatPrice(order.total_cents)}</span>
          </div>

          {/* Only until it ships: after that the server says no anyway */}
          {order.status === "paid" && (
            <div className="mt-4 sm:ml-auto sm:w-64">
              <ErrorText message={cancel.error} />
              <Button variant="secondary" loading={cancel.loading} onClick={cancelOrder}>
                Cancel order
              </Button>
            </div>
          )}
        </>
      ) : (
        !error && <p className="text-sm text-neutral-500">Loading…</p>
      )}

      <div className="mt-6 flex gap-6 text-sm">
        <Link href="/orders" className="text-blue-600 hover:underline">
          ← My orders
        </Link>
        <Link href="/shop" className="text-blue-600 hover:underline">
          Keep shopping →
        </Link>
      </div>
    </Page>
  );
}
