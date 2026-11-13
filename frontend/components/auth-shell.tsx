import Link from "next/link";
import type { ReactNode } from "react";

import { ShieldIcon } from "@/components/icons";
import { StoreLogo } from "@/components/store-logo";
import { STORE_NAME } from "@/lib/store";

/**
 * The full-page look for logging in and registering:
 * gradient background, the shop's name, a link in the top-right corner,
 * the big welcome in the middle and a white card under it for the form.
 *
 * Sizes are compact by default, so the page fits in one screen without a scrollbar.
 * Classes starting with [@media(min-height:900px)]: only apply on windows at least
 * 900px high, where there is room to make everything bigger.
 */
export function AuthShell({
  children,
  topRight = <AdminLoginLink />,
  subtitle = "Good things at sasta prices.",
}: {
  children: ReactNode;
  topRight?: ReactNode;
  subtitle?: string;
}) {
  return (
    <div className="relative flex min-h-dvh flex-1 flex-col overflow-hidden bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-700 text-white">
      {/* Soft blurred circles for decoration */}
      <div className="pointer-events-none absolute -top-32 -left-32 h-96 w-96 rounded-full bg-sky-400/30 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 -bottom-32 h-[28rem] w-[28rem] rounded-full bg-fuchsia-500/30 blur-3xl" />
      <div className="pointer-events-none absolute top-1/3 right-1/4 h-40 w-40 rounded-full bg-white/10 blur-2xl" />

      <header className="relative mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-8 sm:py-4">
        <StoreLogo light />
        {topRight}
      </header>

      <main className="relative flex flex-1 flex-col items-center justify-center px-4 py-2 [@media(min-height:900px)]:py-6">
        <WelcomeHeading />
        <p className="mt-1 text-center text-base text-white/80 [@media(min-height:900px)]:mt-3 [@media(min-height:900px)]:text-lg">{subtitle}</p>

        {/* [&_label]:mb-3 = a little less space under each form field on short screens */}
        <div className="mt-4 w-full max-w-md rounded-3xl bg-white px-6 py-5 text-neutral-900 shadow-2xl ring-1 ring-black/5 [&_label]:mb-3 [@media(min-height:900px)]:mt-8 [@media(min-height:900px)]:p-8 [@media(min-height:900px)]:[&_label]:mb-4 dark:bg-neutral-900 dark:text-neutral-100">
          {children}
        </div>
      </main>

      <footer className="relative hidden py-4 text-center text-xs text-white/60 [@media(min-height:900px)]:block">{STORE_NAME}</footer>
    </div>
  );
}

/**
 * The big three-line greeting, for use on a coloured background:
 *   Welcome            (bold)
 *   to                 (normal)
 *   SASTA ONLINE STORE (very large, with a white-to-gold shine)
 */
export function WelcomeHeading({ className = "" }: { className?: string }) {
  return (
    <h1 className={`text-center text-white ${className}`}>
      <span className="block text-2xl leading-tight font-bold sm:text-3xl [@media(min-height:900px)]:text-4xl">
        Welcome
      </span>
      <span className="block text-base leading-tight font-normal text-white/80 sm:text-xl [@media(min-height:900px)]:mt-1 [@media(min-height:900px)]:text-2xl">
        to
      </span>
      <span className="block bg-gradient-to-r from-white via-amber-100 to-amber-300 bg-clip-text pb-1 text-4xl leading-tight font-extrabold tracking-tight text-transparent drop-shadow-sm sm:text-5xl [@media(min-height:900px)]:mt-2 [@media(min-height:900px)]:sm:text-7xl">
        {STORE_NAME}
      </span>
    </h1>
  );
}

/** "Admin Login" button for the top-right corner. */
export function AdminLoginLink() {
  return (
    <Link
      href="/admin/login"
      className="flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2 text-sm font-medium text-white ring-1 ring-white/30 backdrop-blur transition hover:bg-white/20"
    >
      <ShieldIcon className="h-4 w-4" />
      Admin Login
    </Link>
  );
}

/** "Log in | Register" switch at the top of the customer card. */
export function CustomerTabs({ active }: { active: "login" | "register" }) {
  const tab = (href: string, label: string, isActive: boolean) => (
    <Link
      href={href}
      className={`flex-1 rounded-lg py-2 text-center text-sm font-medium transition ${
        isActive
          ? "bg-white text-indigo-700 shadow-sm dark:bg-neutral-700 dark:text-white"
          : "text-neutral-500 hover:text-neutral-900 dark:hover:text-white"
      }`}
    >
      {label}
    </Link>
  );
  return (
    <div className="mb-4 flex gap-1 rounded-xl bg-neutral-100 p-1 [@media(min-height:900px)]:mb-6 dark:bg-neutral-800">
      {tab("/login", "Log in", active === "login")}
      {tab("/signup", "Register", active === "register")}
    </div>
  );
}
