import { Suspense } from "react";

import { OrderDetail } from "@/components/order-detail";
import { Loading } from "@/components/ui";

/** One order. The [id] in the folder name is the order id from the link. */
export default function OrderPage() {
  // The id is only known when someone opens the page, so Next.js needs a
  // Suspense fallback to show while it reads it (because cacheComponents is on)
  return (
    <Suspense fallback={<Loading />}>
      <OrderDetail />
    </Suspense>
  );
}
