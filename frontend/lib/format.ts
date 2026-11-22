export function fmtPct(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  return `${v.toFixed(digits)}%`;
}

export function fmtSignedPct(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

export function fmtMoney(v: number | null | undefined, currency = "€"): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const sign = v < 0 ? "−" : "";
  return `${sign}${currency}${Math.abs(v).toLocaleString("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function fmtOdds(v: number | null | undefined): string {
  if (v === null || v === undefined) return "–";
  return v.toFixed(2);
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "–";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "–";
  return d.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtAgo(iso: string | null | undefined): string {
  if (!iso) return "–";
  const d = new Date(iso).getTime();
  if (Number.isNaN(d)) return "–";
  const s = Math.max(0, (Date.now() - d) / 1000);
  if (s < 60) return `${Math.round(s)}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
}

export function fmtDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "–";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  return `${(seconds / 3600).toFixed(1)} h`;
}

export function outcomeLabel(outcome: string): string {
  const map: Record<string, string> = {
    home: "1 (Home)",
    away: "2 (Away)",
    draw: "X (Draw)",
    over: "Over",
    under: "Under",
  };
  return map[outcome] ?? outcome.replace(/_/g, " ").toUpperCase();
}
