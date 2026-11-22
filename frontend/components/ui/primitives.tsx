import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, SelectHTMLAttributes, ReactNode } from "react";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-md border border-line bg-surface",
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({
  title,
  subtitle,
  right,
  className,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4 border-b border-line px-4 py-3",
        className
      )}
    >
      <div>
        <h2 className="text-[13px] font-semibold tracking-wide text-bright">
          {title}
        </h2>
        {subtitle ? (
          <p className="mt-0.5 text-xs text-muted">{subtitle}</p>
        ) : null}
      </div>
      {right}
    </div>
  );
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-4", className)} {...props} />;
}

type BadgeVariant = "default" | "positive" | "negative" | "warn" | "outline" | "live";

export function Badge({
  children,
  variant = "default",
  className,
}: {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}) {
  const variants: Record<BadgeVariant, string> = {
    default: "bg-raised text-dim border-line",
    positive: "bg-accent-dim text-accent border-accent/30",
    negative: "bg-risk-dim text-risk border-risk/30",
    warn: "bg-[#332b12] text-warn border-warn/30",
    outline: "bg-transparent text-muted border-line",
    live: "bg-accent-dim text-accent border-accent/40",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

export function Button({
  variant = "default",
  size = "md",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "primary" | "ghost" | "danger";
  size?: "sm" | "md";
}) {
  const variants = {
    default:
      "bg-raised text-bright border border-line hover:bg-hover hover:border-[#2a3140]",
    primary:
      "bg-accent text-[#04130c] border border-accent hover:bg-[#4ee2a4] font-semibold",
    ghost: "bg-transparent text-dim border border-transparent hover:bg-hover hover:text-bright",
    danger:
      "bg-risk-dim text-risk border border-risk/30 hover:bg-risk hover:text-white",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-md transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "px-2 py-1 text-xs" : "px-3 py-1.5 text-[13px]",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-md border border-line bg-ink px-2.5 py-1.5 text-[13px] text-bright placeholder:text-muted/60 outline-none transition-colors focus:border-accent/50 focus:ring-1 focus:ring-accent/20",
        className
      )}
      {...props}
    />
  );
}

export function Select({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "w-full appearance-none rounded-md border border-line bg-ink px-2.5 py-1.5 text-[13px] text-bright outline-none transition-colors focus:border-accent/50 focus:ring-1 focus:ring-accent/20",
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Label({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <label className={cn("mb-1 block text-[11px] font-medium uppercase tracking-wider text-muted", className)}>
      {children}
    </label>
  );
}

export function StatCard({
  label,
  value,
  hint,
  tone = "neutral",
  icon,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "neutral" | "positive" | "negative";
  icon?: ReactNode;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <p className="text-[11px] font-medium uppercase tracking-wider text-muted">
          {label}
        </p>
        {icon ? <span className="text-muted">{icon}</span> : null}
      </div>
      <p
        className={cn(
          "tabular mt-2 text-2xl font-semibold",
          tone === "positive" && "text-accent",
          tone === "negative" && "text-risk",
        )}
      >
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </Card>
  );
}

export function EmptyState({ message, hint }: { message: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 px-4 py-12 text-center">
      <p className="text-sm text-dim">{message}</p>
      {hint ? <p className="text-xs text-muted">{hint}</p> : null}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-risk/30 bg-risk-dim px-4 py-3 text-[13px] text-risk">
      {message}
    </div>
  );
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-9 animate-pulse rounded bg-raised" />
      ))}
    </div>
  );
}

export function Disclaimer({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-md border border-warn/25 bg-[#191705] px-3 py-2 text-[11px] leading-relaxed text-warn/90">
      {children}
    </p>
  );
}
