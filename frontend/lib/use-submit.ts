"use client";

import { useState } from "react";

import { messageFrom } from "@/lib/api";

/** Runs a form action while tracking "loading" and any error message to show. */
export function useSubmit() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function run(action: () => Promise<void>) {
    setError(null);
    setLoading(true);
    try {
      await action();
    } catch (err) {
      setError(messageFrom(err));
    } finally {
      setLoading(false);
    }
  }

  return { error, loading, run };
}
