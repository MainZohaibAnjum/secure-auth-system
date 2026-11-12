"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ProductForm } from "@/components/product-form";
import { Button, ErrorText, Loading, Page } from "@/components/ui";
import { api, messageFrom } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatPrice } from "@/lib/money";
import type { Product } from "@/lib/types";
import { useSubmit } from "@/lib/use-submit";

/** Admins only: add, change, hide and delete products. */
export default function AdminProductsPage() {
  const { status, user } = useAuth();
  const router = useRouter();
  const { error, loading, run } = useSubmit();
  const [products, setProducts] = useState<Product[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  // null = just the list, "new" = the add form, a product = editing that product
  const [editing, setEditing] = useState<Product | "new" | null>(null);
  // Bump this number to load the list again
  const [version, setVersion] = useState(0);
  const isAdmin = user?.role === "admin";

  // Not logged in? Go to the login page.
  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);

  useEffect(() => {
    if (!isAdmin) return;
    let cancelled = false; // ignore the answer if this page was closed meanwhile
    api<Product[]>("/admin/products", { auth: true })
      .then((data) => {
        if (!cancelled) setProducts(data);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(messageFrom(err));
      });
    return () => {
      cancelled = true;
    };
  }, [isAdmin, version]);

  if (status !== "authenticated" || !user) {
    return <Loading />;
  }

  function saved() {
    setEditing(null);
    setVersion((v) => v + 1);
  }

  function toggleHidden(product: Product) {
    run(async () => {
      await api(`/admin/products/${product.id}`, {
        method: "PATCH",
        body: { is_active: !product.is_active },
        auth: true,
      });
      setVersion((v) => v + 1);
    });
  }

  function remove(product: Product) {
    if (!window.confirm(`Delete "${product.name}" for good?`)) return;
    run(async () => {
      await api(`/admin/products/${product.id}`, { method: "DELETE", auth: true });
      setVersion((v) => v + 1);
    });
  }

  return (
    <Page title="Products">
      {!isAdmin ? (
        <ErrorText message="Admins only." />
      ) : (
        <>
          <ErrorText message={error ?? loadError} />

          {editing ? (
            <ProductForm
              // A new key resets the form's boxes when you switch to another product
              key={editing === "new" ? "new" : editing.id}
              product={editing === "new" ? undefined : editing}
              onSaved={saved}
              onCancel={() => setEditing(null)}
            />
          ) : (
            <div className="mb-6 max-w-xs">
              <Button onClick={() => setEditing("new")}>Add a product</Button>
            </div>
          )}

          {products === null ? (
            !loadError && <p className="text-sm text-neutral-500">Loading…</p>
          ) : products.length === 0 ? (
            <p className="text-sm text-neutral-500">No products yet.</p>
          ) : (
            <ul className="divide-y divide-neutral-200 dark:divide-neutral-800">
              {products.map((product) => (
                <li key={product.id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {product.name}
                      {!product.is_active && (
                        <span className="ml-2 rounded bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600 dark:bg-neutral-900 dark:text-neutral-400">
                          Hidden
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-neutral-500">
                      {formatPrice(product.price_cents)} · {product.stock} in stock
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-3 text-sm">
                    <button
                      type="button"
                      onClick={() => setEditing(product)}
                      className="text-blue-600 hover:underline"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleHidden(product)}
                      disabled={loading}
                      className="text-blue-600 hover:underline disabled:opacity-50"
                    >
                      {product.is_active ? "Hide" : "Show"}
                    </button>
                    <button
                      type="button"
                      onClick={() => remove(product)}
                      disabled={loading}
                      className="text-red-600 hover:underline disabled:opacity-50"
                    >
                      Delete
                    </button>
                  </div>
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
