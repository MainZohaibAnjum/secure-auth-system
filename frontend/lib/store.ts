// The shop's name comes from frontend/.env.local, like every other setting.

const name = process.env.NEXT_PUBLIC_STORE_NAME;

if (!name) {
  throw new Error("NEXT_PUBLIC_STORE_NAME is missing. Add it to frontend/.env.local");
}

export const STORE_NAME: string = name;
