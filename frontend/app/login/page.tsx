import Link from "next/link";

import { AuthShell, CustomerTabs } from "@/components/auth-shell";
import { LoginForm } from "@/components/login-form";

/** Customer login: full-page welcome, with the form in the middle. */
export default function LoginPage() {
  return (
    <AuthShell>
      <CustomerTabs active="login" />
      <LoginForm />
      <p className="mt-4 text-center text-sm text-neutral-500">
        New here?{" "}
        <Link href="/signup" className="font-medium text-blue-600 hover:underline">
          Create a free account
        </Link>
      </p>
    </AuthShell>
  );
}
