import { Suspense } from "react";

import { ProductDetail } from "@/components/product-detail";
import { Loading } from "@/components/ui";

/** One product. The [id] in the folder name is the product id from the link. */
export default function ProductPage() {
  // The id is only known when someone opens the page, so Next.js needs a
  // Suspense fallback to show while it reads it (because cacheComponents is on)
  return (
    <Suspense fallback={<Loading />}>
      <ProductDetail />
    </Suspense>
  );
}
