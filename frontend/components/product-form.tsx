"use client";

import { useState, type FormEvent } from "react";

import { Button, ErrorText, Field, TextArea } from "@/components/ui";
import { api } from "@/lib/api";
import { centsToText, parsePrice } from "@/lib/money";
import type { Product, ProductInput } from "@/lib/types";
import { useSubmit } from "@/lib/use-submit";

type Props = {
  product?: Product; // given = edit this product, missing = add a new one
  onSaved: () => void;
  onCancel: () => void;
};

/** The admin form for adding a product or changing one. */
export function ProductForm({ product, onSaved, onCancel }: Props) {
  const { error, loading, run } = useSubmit();
  const [name, setName] = useState(product?.name ?? "");
  const [price, setPrice] = useState(product ? centsToText(product.price_cents) : "");
  const [stock, setStock] = useState(product ? String(product.stock) : "");
  const [imageUrl, setImageUrl] = useState(product?.image_url ?? "");
  const [description, setDescription] = useState(product?.description ?? "");
  const [isActive, setIsActive] = useState(product?.is_active ?? true);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    run(async () => {
      const priceCents = parsePrice(price);
      if (priceCents === null) {
        throw new Error("Price must look like 19.99");
      }
      const body: ProductInput = {
        name,
        description,
        price_cents: priceCents,
        stock: Number(stock),
        image_url: imageUrl.trim() || null,
        is_active: isActive,
      };
      if (product) {
        await api(`/admin/products/${product.id}`, { method: "PATCH", body, auth: true });
      } else {
        await api("/admin/products", { method: "POST", body, auth: true });
      }
      onSaved();
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-6 rounded-xl border border-neutral-200 p-4 dark:border-neutral-800"
    >
      <h2 className="mb-4 font-semibold">{product ? `Edit: ${product.name}` : "New product"}</h2>
      <ErrorText message={error} />

      <Field label="Name" value={name} onChange={(e) => setName(e.target.value)} maxLength={200} required />
      <div className="grid grid-cols-2 gap-3">
        <Field
          label="Price (e.g. 19.99)"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          inputMode="decimal"
          required
        />
        <Field
          label="Stock"
          type="number"
          value={stock}
          onChange={(e) => setStock(e.target.value)}
          min={0}
          step={1}
          required
        />
      </div>
      <Field
        label="Image link (optional)"
        type="url"
        value={imageUrl}
        onChange={(e) => setImageUrl(e.target.value)}
        placeholder="https://…"
        maxLength={500}
      />
      <TextArea
        label="Description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        rows={4}
        maxLength={5000}
      />
      <label className="mb-4 flex items-center gap-2 text-sm">
        <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
        Show in the shop
      </label>

      <div className="space-y-2">
        <Button type="submit" loading={loading}>
          {product ? "Save changes" : "Add product"}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
