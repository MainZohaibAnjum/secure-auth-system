import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

/** A centered box with a title, used by every page. */
export function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="flex flex-1 items-center justify-center p-4">
      <div className="w-full max-w-sm rounded-2xl border border-neutral-200 p-6 shadow-sm dark:border-neutral-800">
        <h1 className="mb-6 text-2xl font-semibold">{title}</h1>
        {children}
      </div>
    </main>
  );
}

/** A labelled text box. */
export function Field({ label, ...props }: { label: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="mb-4 block text-sm">
      <span className="mb-1 block font-medium">{label}</span>
      <input
        {...props}
        className="w-full rounded-lg border border-neutral-300 bg-transparent px-3 py-2 outline-none focus:border-blue-600 dark:border-neutral-700"
      />
    </label>
  );
}

type ButtonProps = {
  loading?: boolean;
  variant?: "primary" | "secondary";
} & ButtonHTMLAttributes<HTMLButtonElement>;

export function Button({ loading, variant = "primary", children, disabled, ...props }: ButtonProps) {
  const colors =
    variant === "primary"
      ? "bg-blue-600 text-white hover:bg-blue-700"
      : "border border-neutral-300 hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900";
  return (
    <button
      {...props}
      disabled={loading || disabled}
      className={`w-full rounded-lg px-4 py-2 font-medium disabled:opacity-50 ${colors}`}
    >
      {loading ? "Please wait…" : children}
    </button>
  );
}

export function ErrorText({ message }: { message: string | null }) {
  if (!message) {
    return null;
  }
  return (
    <p
      role="alert"
      className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
    >
      {message}
    </p>
  );
}

/** Shown while we check whether the user is logged in. */
export function Loading() {
  return <main className="flex flex-1 items-center justify-center p-4 text-neutral-500">Loading…</main>;
}
