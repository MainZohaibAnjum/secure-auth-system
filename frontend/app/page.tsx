"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { WelcomeHeading } from "@/components/auth-shell";
import { ArrowRightIcon, BagIcon, BoxIcon, ShieldIcon } from "@/components/icons";
import { ProductImage } from "@/components/product-image";
import { StoreLogo } from "@/components/store-logo";
import { Loading } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatPrice } from "@/lib/money";
import { STORE_NAME } from "@/lib/store";
import type { Product } from "@/lib/types";

// How many products the home page shows as a preview
const PREVIEW_COUNT = 4;

/** The front door of the shop: log in or register. Logged-in users go to their dashboard. */
export default function Home() {
  const { status } = useAuth();
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard");
  }, [status, router]);

  // A few products to show off. Anyone may see them, so no login is needed.
  useEffect(() => {
    let cancelled = false; // ignore the answer if this page was closed meanwhile
    api<Product[]>("/products")
      .then((data) => {
        if (!cancelled) setProducts(data.slice(0, PREVIEW_COUNT));
      })
      .catch(() => {
        // No preview then; the rest of the page still works
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // While we check the login (or move to the dashboard), show nothing else
  if (status !== "anonymous") {
    return <Loading />;
  }

  return (
    <div className="flex flex-1 flex-col bg-neutral-50 dark:bg-neutral-950">
      {/* ---------- Top bar ---------- */}
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-3 sm:px-8">
        <StoreLogo />
        <Link
          href="/admin/login"
          className="flex items-center gap-2 rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-medium shadow-sm transition hover:border-amber-400 hover:text-amber-700 dark:border-neutral-700 dark:bg-neutral-900"
        >
          <ShieldIcon className="h-4 w-4" />
          Admin Login
        </Link>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 space-y-8 px-4 pb-10 sm:px-8">
        {/* ---------- Welcome ---------- */}
        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-600 px-6 py-8 text-center text-white shadow-lg sm:px-12 [@media(min-height:900px)]:py-12">
          <div className="pointer-events-none absolute -top-20 -left-20 h-64 w-64 rounded-full bg-white/10" />
          <div className="pointer-events-none absolute -right-16 -bottom-24 h-72 w-72 rounded-full bg-white/10" />

          <div className="relative">
            <WelcomeHeading />
            <p className="mx-auto mt-2 max-w-xl text-white/80 [@media(min-height:900px)]:mt-4 [@media(min-height:900px)]:text-lg">
              Good things at sasta prices. Make a free account, fill your cart and track every order
              in one place.
            </p>

            <div className="mx-auto mt-6 flex max-w-sm flex-col gap-3 sm:flex-row [@media(min-height:900px)]:mt-8">
              <Link
                href="/signup"
                className="flex-1 rounded-xl bg-white px-5 py-3 font-semibold text-indigo-700 shadow-sm transition hover:bg-indigo-50"
              >
                Register free
              </Link>
              <Link
                href="/login"
                className="flex-1 rounded-xl px-5 py-3 font-semibold ring-1 ring-white/50 transition hover:bg-white/10"
              >
                Log in
              </Link>
            </div>

            <Link
              href="/shop"
              className="mt-4 inline-flex items-center gap-1 text-sm text-white/80 hover:text-white [@media(min-height:900px)]:mt-6"
            >
              or just look around the shop <ArrowRightIcon className="h-4 w-4" />
            </Link>
          </div>
        </section>

        {/* ---------- Why shop here ---------- */}
        <section className="grid gap-4 sm:grid-cols-3">
          <Feature icon={<BagIcon />} title="Sasta prices">
            Fair prices on everything, always shown before you buy.
          </Feature>
          <Feature icon={<ShieldIcon />} title="Safe account">
            Strong passwords and optional two-factor login keep your account yours.
          </Feature>
          <Feature icon={<BoxIcon />} title="Track your orders">
            See every order and its status, and cancel before it ships.
          </Feature>
        </section>

        {/* ---------- Product preview ---------- */}
        {products.length > 0 && (
          <section>
            <div className="mb-4 flex items-end justify-between">
              <h2 className="text-xl font-semibold">Fresh in the shop</h2>
              <Link href="/shop" className="text-sm text-blue-600 hover:underline">
                See all →
              </Link>
            </div>
            <ul className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {products.map((product) => (
                <li key={product.id}>
                  <Link
                    href={`/shop/${product.id}`}
                    className="block rounded-2xl border border-neutral-200 bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-neutral-800 dark:bg-neutral-900"
                  >
                    <ProductImage url={product.image_url} name={product.name} />
                    <p className="mt-2 truncate font-medium">{product.name}</p>
                    <p className="text-sm text-neutral-500">{formatPrice(product.price_cents)}</p>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>

      <footer className="border-t border-neutral-200 py-4 text-center text-sm text-neutral-500 dark:border-neutral-800">
        {STORE_NAME}
      </footer>
    </div>
  );
}

function Feature({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-300">
        {icon}
      </div>
      <p className="font-medium">{title}</p>
      <p className="mt-1 text-sm text-neutral-500">{children}</p>
    </div>
  );
}
