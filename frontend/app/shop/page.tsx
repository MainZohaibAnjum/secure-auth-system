"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ProductImage } from "@/components/product-image";
import { ErrorText, Page } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { formatPrice } from "@/lib/money";
import type { Product } from "@/lib/types";

/** The shop window: every product for sale. Anyone can look, no login needed. */
export default function ShopPage() {
  const [products, setProducts] = useState<Product[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false; // ignore the answer if this page was closed meanwhile
    api<Product[]>("/products")
      .then((data) => {
        if (!cancelled) setProducts(data);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(messageFrom(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Page title="Shop">
      <ErrorText message={loadError} />

      {products === null ? (
        !loadError && <p className="text-sm text-neutral-500">Loading…</p>
      ) : products.length === 0 ? (
        <p className="text-sm text-neutral-500">No products yet.</p>
      ) : (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {products.map((product) => (
            <li key={product.id}>
              <Link
                href={`/shop/${product.id}`}
                className="block rounded-xl border border-neutral-200 p-3 hover:border-blue-600 dark:border-neutral-800"
              >
                <ProductImage url={product.image_url} name={product.name} />
                <p className="mt-2 truncate font-medium">{product.name}</p>
                <p className="text-sm text-neutral-500">
                  {formatPrice(product.price_cents)}
                  {product.stock === 0 && <span className="text-red-600"> · Sold out</span>}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <Link href="/dashboard" className="mt-6 inline-block text-sm text-blue-600 hover:underline">
        ← My account
      </Link>
    </Page>
  );
}
