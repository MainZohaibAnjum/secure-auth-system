// Turn raw session data into words people understand

/** "Mozilla/5.0 (Windows NT 10.0; ...) Chrome/..." → "Chrome on Windows" */
export function describeDevice(userAgent: string | null): string {
  if (!userAgent) {
    return "Unknown device";
  }
  // Order matters: Edge and Opera also say "Chrome", Chrome also says "Safari"
  const browser = /Edg\//.test(userAgent)
    ? "Edge"
    : /OPR\//.test(userAgent)
      ? "Opera"
      : /Firefox\//.test(userAgent)
        ? "Firefox"
        : /Chrome\//.test(userAgent)
          ? "Chrome"
          : /Safari\//.test(userAgent)
            ? "Safari"
            : null;
  // Android also says "Linux", iPhones also say "Mac OS X"
  const os = /Windows/.test(userAgent)
    ? "Windows"
    : /Android/.test(userAgent)
      ? "Android"
      : /iPhone|iPad/.test(userAgent)
        ? "iOS"
        : /Mac OS X/.test(userAgent)
          ? "macOS"
          : /Linux/.test(userAgent)
            ? "Linux"
            : null;

  if (browser && os) {
    return `${browser} on ${os}`;
  }
  return browser ?? os ?? userAgent.slice(0, 40);
}

/** "2026-11-02T10:00:00Z" → "5 minutes ago" */
export function timeAgo(isoDate: string): string {
  const seconds = Math.round((Date.now() - new Date(isoDate).getTime()) / 1000);
  if (seconds < 60) {
    return "just now";
  }
  const format = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return format.format(-minutes, "minute");
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return format.format(-hours, "hour");
  }
  return format.format(-Math.round(hours / 24), "day");
}
