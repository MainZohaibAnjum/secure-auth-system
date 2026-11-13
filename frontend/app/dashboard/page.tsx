"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import {
  ArrowRightIcon,
  BagIcon,
  BoxIcon,
  CartIcon,
  LogoutIcon,
  ShieldIcon,
  TagIcon,
  UsersIcon,
} from "@/components/icons";
import { StatusBadge } from "@/components/order-status";
import { RecoveryCodesPanel } from "@/components/recovery-codes";
import { SessionsPanel } from "@/components/sessions-panel";
import { StoreLogo } from "@/components/store-logo";
import { TwoFactorPanel } from "@/components/two-factor-panel";
import { Loading } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatPrice } from "@/lib/money";
import type { Cart, Order } from "@/lib/types";

// What the summary tiles show. null = still loading (or couldn't load).
type Summary = { cartItems: number; orderCount: number; latestOrder: Order | null };

export default function DashboardPage() {
  const { status, user, logout } = useAuth();
  const router = useRouter();
  const [summary, setSummary] = useState<Summary | null>(null);

  // Not logged in? Go to the login page.
  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [status, router]);

  // Load the cart and orders at the same time, for the summary tiles
  useEffect(() => {
    if (status !== "authenticated") return;
    let cancelled = false; // ignore the answer if this page was closed meanwhile
    Promise.all([api<Cart>("/cart", { auth: true }), api<Order[]>("/orders", { auth: true })])
      .then(([cart, orders]) => {
        if (cancelled) return;
        setSummary({
          cartItems: cart.items.reduce((sum, line) => sum + line.quantity, 0),
          orderCount: orders.length,
          latestOrder: orders[0] ?? null, // the server sends newest first
        });
      })
      .catch(() => {
        // The tiles just keep showing "–"; the rest of the page still works
      });
    return () => {
      cancelled = true;
    };
  }, [status]);

  if (status !== "authenticated" || !user) {
    return <Loading />;
  }

  const isAdmin = user.role === "admin";
  const latest = summary?.latestOrder;

  return (
    <main className="flex-1 bg-neutral-50 dark:bg-neutral-950">
      <div className="mx-auto w-full max-w-5xl space-y-8 p-4 sm:p-8">
        {/* ---------- Welcome banner ---------- */}
        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-600 p-6 text-white shadow-lg sm:p-8">
          {/* Two soft circles for decoration */}
          <div className="pointer-events-none absolute -top-16 -right-16 h-56 w-56 rounded-full bg-white/10" />
          <div className="pointer-events-none absolute -bottom-20 right-24 h-40 w-40 rounded-full bg-white/10" />

          <div className="relative mb-6 border-b border-white/20 pb-4">
            <StoreLogo light />
          </div>

          <div className="relative flex flex-wrap items-center justify-between gap-6">
            <div className="flex min-w-0 items-center gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white/20 text-2xl font-semibold uppercase ring-1 ring-white/30">
                {user.email[0]}
              </div>
              <div className="min-w-0">
                <p className="text-sm text-white/70">Welcome back</p>
                <h1 className="truncate text-xl font-semibold sm:text-2xl">{user.email}</h1>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                  <span className="rounded-full bg-white/20 px-2.5 py-0.5 font-medium">
                    {isAdmin ? "Admin" : "Customer"}
                  </span>
                  <span className="text-white/70">
                    Member since {new Date(user.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={() => logout()}
              className="flex items-center gap-2 rounded-xl bg-white/15 px-4 py-2 text-sm font-medium ring-1 ring-white/30 transition hover:bg-white/25"
            >
              <LogoutIcon className="h-4 w-4" />
              Log out
            </button>
          </div>
        </section>

        {/* ---------- Summary tiles ---------- */}
        <section className="grid gap-4 sm:grid-cols-3">
          <StatTile
            label="In your cart"
            value={summary ? `${summary.cartItems}` : "–"}
            hint={summary?.cartItems === 1 ? "item" : "items"}
            icon={<CartIcon />}
            color="text-blue-600 bg-blue-50 dark:bg-blue-950 dark:text-blue-300"
          />
          <StatTile
            label="Your orders"
            value={summary ? `${summary.orderCount}` : "–"}
            hint="placed so far"
            icon={<BoxIcon />}
            color="text-violet-600 bg-violet-50 dark:bg-violet-950 dark:text-violet-300"
          />
          <StatTile
            label="Two-factor login"
            value={user.totp_enabled ? "On" : "Off"}
            hint={user.totp_enabled ? "your account is extra safe" : "turn it on below"}
            icon={<ShieldIcon />}
            color={
              user.totp_enabled
                ? "text-green-600 bg-green-50 dark:bg-green-950 dark:text-green-300"
                : "text-amber-600 bg-amber-50 dark:bg-amber-950 dark:text-amber-300"
            }
          />
        </section>

        {/* ---------- Shop on the left, two-factor login on the right ---------- */}
        {/* On a phone the two columns stack: shop first, then 2FA */}
        <div className="grid items-start gap-8 lg:grid-cols-5">
          <div className="space-y-8 lg:col-span-3">
            <section>
              <SectionTitle>Shop</SectionTitle>
              <div className="grid gap-3">
                <ShortcutCard href="/shop" title="Browse the shop" text="See everything for sale" icon={<BagIcon />} />
                <ShortcutCard href="/cart" title="My cart" text="Check out what you picked" icon={<CartIcon />} />
                <ShortcutCard href="/orders" title="My orders" text="Track and cancel orders" icon={<BoxIcon />} />
              </div>
            </section>

            {/* Only a shortcut: the server itself refuses /admin requests from non-admins */}
            {isAdmin && (
              <section>
                <SectionTitle>Admin</SectionTitle>
                <div className="grid gap-3">
                  <ShortcutCard href="/admin" title="Users" text="Every account" icon={<UsersIcon />} admin />
                  <ShortcutCard
                    href="/admin/products"
                    title="Products"
                    text="Add, edit and hide products"
                    icon={<TagIcon />}
                    admin
                  />
                  <ShortcutCard
                    href="/admin/orders"
                    title="Orders"
                    text="Ship, deliver or cancel"
                    icon={<BoxIcon />}
                    admin
                  />
                </div>
              </section>
            )}
          </div>

          <aside className="lg:col-span-2">
            <SectionTitle>Two-factor login</SectionTitle>
            <div className="space-y-6">
              <TwoFactorPanel />
              <RecoveryCodesPanel />
            </div>
          </aside>
        </div>

        {/* ---------- Latest order ---------- */}
        {latest && (
          <section>
            <SectionTitle>Latest order</SectionTitle>
            <Link
              href={`/orders/${latest.id}`}
              className="group flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:shadow-md dark:border-neutral-800 dark:bg-neutral-900"
            >
              <div className="min-w-0">
                <p className="truncate font-medium">
                  {latest.items.map((item) => `${item.quantity} × ${item.product_name}`).join(", ")}
                </p>
                <p className="text-sm text-neutral-500">
                  {new Date(latest.created_at).toLocaleString()}
                </p>
              </div>
              <div className="flex items-center gap-4">
                <StatusBadge status={latest.status} />
                <span className="font-semibold">{formatPrice(latest.total_cents)}</span>
                <ArrowRightIcon className="h-4 w-4 text-neutral-400 transition group-hover:translate-x-1 group-hover:text-blue-600" />
              </div>
            </Link>
          </section>
        )}

        {/* ---------- Devices ---------- */}
        <section>
          <SectionTitle>Security</SectionTitle>
          <SessionsPanel />
        </section>
      </div>
    </main>
  );
}

function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="mb-3 text-sm font-semibold tracking-wide text-neutral-500 uppercase">
      {children}
    </h2>
  );
}

function StatTile({
  label,
  value,
  hint,
  icon,
  color,
}: {
  label: string;
  value: string;
  hint: string;
  icon: ReactNode;
  color: string;
}) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${color}`}>
        {icon}
      </div>
      <div>
        <p className="text-sm text-neutral-500">{label}</p>
        <p className="text-2xl font-semibold">
          {value} <span className="text-sm font-normal text-neutral-500">{hint}</span>
        </p>
      </div>
    </div>
  );
}

function ShortcutCard({
  href,
  title,
  text,
  icon,
  admin = false,
}: {
  href: string;
  title: string;
  text: string;
  icon: ReactNode;
  admin?: boolean;
}) {
  const iconColor = admin
    ? "bg-amber-50 text-amber-600 group-hover:bg-amber-500 dark:bg-amber-950 dark:text-amber-300"
    : "bg-blue-50 text-blue-600 group-hover:bg-blue-600 dark:bg-blue-950 dark:text-blue-300";
  return (
    <Link
      href={href}
      className="group flex items-center gap-4 rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md dark:border-neutral-800 dark:bg-neutral-900"
    >
      <div
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl transition group-hover:text-white ${iconColor}`}
      >
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-medium">{title}</p>
        <p className="truncate text-sm text-neutral-500">{text}</p>
      </div>
      <ArrowRightIcon className="h-4 w-4 shrink-0 text-neutral-300 transition group-hover:translate-x-1 group-hover:text-blue-600" />
    </Link>
  );
}
