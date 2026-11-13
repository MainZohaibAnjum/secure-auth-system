import Link from "next/link";

import { AuthShell } from "@/components/auth-shell";
import { ShieldIcon } from "@/components/icons";
import { LoginForm } from "@/components/login-form";

/** Login for shop staff. Same login as customers; admins land on the admin pages. */
export default function AdminLoginPage() {
  return (
    <AuthShell
      subtitle="Staff area: manage products and orders."
      topRight={
        <Link
          href="/login"
          className="rounded-xl bg-white/10 px-4 py-2 text-sm font-medium text-white ring-1 ring-white/30 backdrop-blur transition hover:bg-white/20"
        >
          ← Customer login
        </Link>
      }
    >
      <div className="mb-4 flex items-center gap-3 [@media(min-height:900px)]:mb-6">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50 text-amber-600 dark:bg-amber-950 dark:text-amber-300">
          <ShieldIcon />
        </div>
        <div>
          <h2 className="text-xl font-semibold">Admin login</h2>
          <p className="text-sm text-neutral-500">Only for admin accounts.</p>
        </div>
      </div>
      <LoginForm admin />
    </AuthShell>
  );
}
