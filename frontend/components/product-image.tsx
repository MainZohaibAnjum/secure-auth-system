/** The product photo, or a grey box when there is none. */
export function ProductImage({ url, name }: { url: string | null; name: string }) {
  if (!url) {
    return <div className="aspect-square w-full rounded-lg bg-neutral-100 dark:bg-neutral-900" />;
  }
  return (
    // A plain <img>, because admins can link a photo from any website,
    // and next/image would need every website listed in next.config.ts
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={url}
      alt={name}
      referrerPolicy="no-referrer"
      className="aspect-square w-full rounded-lg bg-neutral-100 object-cover dark:bg-neutral-900"
    />
  );
}
