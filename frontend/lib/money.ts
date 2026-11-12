// Prices travel as whole cents (1999 = 19.99), so no money is lost to rounding.
// These helpers turn them into text for people, and back.

const CURRENCY = process.env.NEXT_PUBLIC_CURRENCY;

if (!CURRENCY) {
  throw new Error("NEXT_PUBLIC_CURRENCY is missing. Add it to frontend/.env.local");
}

const formatter = new Intl.NumberFormat(undefined, { style: "currency", currency: CURRENCY });

/** 1999 → "$19.99" (the symbol depends on NEXT_PUBLIC_CURRENCY). */
export function formatPrice(cents: number): string {
  return formatter.format(cents / 100);
}

/** 1999 → "19.99", for putting a price into a text box. */
export function centsToText(cents: number): string {
  return `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, "0")}`;
}

/** "19.99" → 1999, "19" → 1900. Returns null if it isn't a price. */
export function parsePrice(text: string): number | null {
  // Read the digits as text, so 19.99 never becomes 1998.9999 on the way
  const match = /^(\d{1,7})(?:\.(\d{1,2}))?$/.exec(text.trim());
  if (!match) {
    return null;
  }
  return Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
}
