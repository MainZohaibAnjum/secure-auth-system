import type { OrderStatus } from "@/lib/types";

const LABELS: Record<OrderStatus, string> = {
  paid: "Paid",
  shipped: "Shipped",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

const COLORS: Record<OrderStatus, string> = {
  paid: "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  shipped: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  delivered: "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300",
  cancelled: "bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400",
};

/** A small coloured label like "Shipped". */
export function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${COLORS[status]}`}>
      {LABELS[status]}
    </span>
  );
}
