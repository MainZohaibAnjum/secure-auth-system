"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ProductImage } from "@/components/product-image";
import { Button, ErrorText, Loading, Page } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatPrice } from "@/lib/money";
import type { Cart } from "@/lib/types";

const smallButton =
  "rounded-lg border border-neutral-300 px-2 py-1 text-sm hover:bg-neutral-100 disabled:opacity-40 dark:border-neutral-700 dark:hover:bg-neutral-900";

/** The logged-in user's cart: change quantities, remove things, see the total. */
export default function CartPage() {
  const { status } = useAuth();
  const router = useRouter();
  const [cart, setCart] = useState<Cart | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false); // stops double clicks while a change is saving

  // Not logged in? Go to the login page.
  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);

  useEffect(() => {
    if (status !== "authenticated") return;
    let cancelled = false; // ignore the answer if this page was closed meanwhile
    api<Cart>("/cart", { auth: true })
      .then((data) => {
        if (!cancelled) setCart(data);
      })
      .catch((err) => {
        if (!cancelled) setError(messageFrom(err));
      });
    return () => {
      cancelled = true;
    };
  }, [status]);

  /** Send one change to the server, then show the cart it sends back. */
  async function change(path: string, method: "PATCH" | "DELETE", body?: unknown) {
    setError(null);
    setBusy(true);
    try {
      setCart(await api<Cart>(path, { method, body, auth: true }));
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }

  if (status !== "authenticated") {
    return <Loading />;
  }

  return (
    <Page title="Your cart">
      <ErrorText message={error} />

      {cart === null ? (
        !error && <p className="text-sm text-neutral-500">Loading…</p>
      ) : cart.items.length === 0 ? (
        <p className="text-sm text-neutral-500">Your cart is empty.</p>
      ) : (
        <>
          <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
            {cart.items.map(({ product, quantity, line_total_cents }) => {
              const url = `/cart/items/${product.id}`;
              return (
                <li key={product.id} className="flex items-center gap-4 py-4">
                  <Link href={`/shop/${product.id}`} className="w-16 shrink-0">
                    <ProductImage url={product.image_url} name={product.name} />
                  </Link>

                  <div className="min-w-0 flex-1">
                    <Link href={`/shop/${product.id}`} className="block truncate font-medium hover:underline">
                      {product.name}
                    </Link>
                    <p className="text-sm text-neutral-500">{formatPrice(product.price_cents)} each</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      className={smallButton}
                      disabled={busy || quantity <= 1}
                      onClick={() => change(url, "PATCH", { quantity: quantity - 1 })}
                      aria-label={`One less ${product.name}`}
                    >
                      −
                    </button>
                    <span className="w-6 text-center">{quantity}</span>
                    <button
                      className={smallButton}
                      disabled={busy || quantity >= product.stock}
                      onClick={() => change(url, "PATCH", { quantity: quantity + 1 })}
                      aria-label={`One more ${product.name}`}
                    >
                      +
                    </button>
                  </div>

                  <div className="w-24 text-right">
                    <p className="font-medium">{formatPrice(line_total_cents)}</p>
                    <button
                      className="text-xs text-red-600 hover:underline disabled:opacity-40"
                      disabled={busy}
                      onClick={() => change(url, "DELETE")}
                    >
                      Remove
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>

          <div className="mt-4 flex items-center justify-between border-t border-neutral-200 pt-4 text-lg font-semibold dark:border-neutral-800">
            <span>Total</span>
            <span>{formatPrice(cart.total_cents)}</span>
          </div>

          {/* Checkout is the next step (orders); for now the button is switched off */}
          <div className="mt-4 sm:ml-auto sm:w-64">
            <Button disabled>Checkout (coming soon)</Button>
          </div>
        </>
      )}

      <Link href="/shop" className="mt-6 inline-block text-sm text-blue-600 hover:underline">
        ← Keep shopping
      </Link>
    </Page>
  );
}
