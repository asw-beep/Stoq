// Display formatters shared across the dashboard.

export function fmtCurrency(n?: number | null, dash = "—"): string {
  if (n == null) return dash;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(n);
}

export function fmtNumber(n?: number | null, dash = "—"): string {
  if (n == null) return dash;
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(n);
}

export function fmtPercent(n?: number | null, dash = "—"): string {
  if (n == null) return dash;
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

export function fmtSignedCurrency(n?: number | null, dash = "—"): string {
  if (n == null) return dash;
  return `${n >= 0 ? "+" : "-"}${fmtCurrency(Math.abs(n))}`;
}

export function fmtDate(s?: string | null, dash = "—"): string {
  if (!s) return dash;
  return new Date(s).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// Tailwind text color by sign (emerald gain / red loss).
export function changeColor(n?: number | null): string {
  if (n == null || n === 0) return "text-muted-foreground";
  return n > 0 ? "text-emerald-600" : "text-red-600";
}
