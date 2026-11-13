import Link from "next/link";

import { BagIcon } from "@/components/icons";
import { STORE_NAME } from "@/lib/store";

/** The shop's name with a bag icon. Clicking it goes to the home page. */
export function StoreLogo({ light = false }: { light?: boolean }) {
  return (
    <Link href="/" className="inline-flex items-center gap-2 font-semibold tracking-tight">
      <span
        className={`flex h-8 w-8 items-center justify-center rounded-lg ${
          light ? "bg-white/20 text-white" : "bg-gradient-to-br from-blue-600 to-violet-600 text-white"
        }`}
      >
        <BagIcon className="h-4.5 w-4.5" />
      </span>
      <span className={light ? "text-white" : ""}>{STORE_NAME}</span>
    </Link>
  );
}
