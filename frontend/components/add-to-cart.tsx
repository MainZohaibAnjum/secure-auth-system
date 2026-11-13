"use client";

import Link from "next/link";
import { useState } from "react";

import { Button, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Cart, Product } from "@/lib/types";
import { useSubmit } from "@/lib/use-submit";

// The quantity list shows at most this many choices (the server checks the real stock)
const MAX_CHOICES = 10;

/** "Add to cart" on the product page: pick how many, then add. */
export function AddToCart({ product }: { product: Product }) {
  const { status } = useAuth();
  const { error, loading, run } = useSubmit();
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);

  if (product.stock === 0) {
    return null; // the page already says "Sold out"
  }

  if (status !== "authenticated") {
    return (
      <Link href="/login" className="text-sm text-blue-600 hover:underline">
        Log in to buy →
      </Link>
    );
  }

  const choices = Array.from({ length: Math.min(product.stock, MAX_CHOICES) }, (_, i) => i + 1);

  function addToCart() {
    run(async () => {
      setAdded(false);
      await api<Cart>("/cart/items", {
        method: "POST",
        auth: true,
        body: { product_id: product.id, quantity },
      });
      setAdded(true);
    });
  }

  return (
    <div>
      <ErrorText message={error} />
      <label className="mb-3 flex items-center gap-2 text-sm">
        <span className="font-medium">Quantity</span>
        <select
          value={quantity}
          onChange={(e) => setQuantity(Number(e.target.value))}
          className="rounded-lg border border-neutral-300 bg-transparent px-2 py-1 dark:border-neutral-700"
        >
          {choices.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </label>
      <Button loading={loading} onClick={addToCart}>
        Add to cart
      </Button>
      {added && (
        <p className="mt-3 text-sm text-green-600">
          Added to your cart.{" "}
          <Link href="/cart" className="text-blue-600 hover:underline">
            View cart →
          </Link>
        </p>
      )}
    </div>
  );
}
