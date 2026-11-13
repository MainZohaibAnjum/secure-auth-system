"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AddToCart } from "@/components/add-to-cart";
import { ProductImage } from "@/components/product-image";
import { ErrorText, Page } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { formatPrice } from "@/lib/money";
import type { Product } from "@/lib/types";

/** Everything about one product: photo, price, stock and description. */
export function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false; // ignore the answer if this page was closed meanwhile
    api<Product>(`/products/${encodeURIComponent(id)}`)
      .then((data) => {
        if (!cancelled) setProduct(data);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(messageFrom(err));
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <Page title={product?.name ?? "Product"}>
      <ErrorText message={loadError} />

      {product ? (
        <div className="grid gap-6 sm:grid-cols-2">
          <ProductImage url={product.image_url} name={product.name} />
          <div>
            <p className="text-2xl font-semibold">{formatPrice(product.price_cents)}</p>
            <p className="mb-4 text-sm">
              {product.stock > 0 ? (
                <span className="text-green-600">In stock: {product.stock}</span>
              ) : (
                <span className="text-red-600">Sold out</span>
              )}
            </p>
            <p className="whitespace-pre-line text-sm text-neutral-600 dark:text-neutral-400">
              {product.description}
            </p>
            <div className="mt-6">
              <AddToCart product={product} />
            </div>
          </div>
        </div>
      ) : (
        !loadError && <p className="text-sm text-neutral-500">Loading…</p>
      )}

      <Link href="/shop" className="mt-6 inline-block text-sm text-blue-600 hover:underline">
        ← Back to the shop
      </Link>
    </Page>
  );
}
