"use client";

import type { ReactNode } from "react";

type BadgeVariant = "success" | "warning" | "danger" | "info" | "neutral" | "accent";

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
  className?: string;
}

const variantMap: Record<BadgeVariant, { bg: string; text: string; border: string }> = {
  success: {
    bg: "var(--success-dim)",
    text: "var(--success)",
    border: "rgba(34,197,94,0.25)",
  },
  warning: {
    bg: "var(--warning-dim)",
    text: "var(--warning)",
    border: "rgba(245,158,11,0.25)",
  },
  danger: {
    bg: "var(--danger-dim)",
    text: "var(--danger)",
    border: "rgba(239,68,68,0.25)",
  },
  info: {
    bg: "var(--info-dim)",
    text: "var(--info)",
    border: "rgba(59,130,246,0.25)",
  },
  neutral: {
    bg: "var(--bg-overlay)",
    text: "var(--text-secondary)",
    border: "var(--border)",
  },
  accent: {
    bg: "var(--accent-dim)",
    text: "var(--accent)",
    border: "rgba(124,58,237,0.3)",
  },
};

export function Badge({
  variant = "neutral",
  children,
  className = "",
}: BadgeProps) {
  const { bg, text, border } = variantMap[variant];

  return (
    <span
      className={[
        "inline-flex items-center gap-1 px-2 py-0.5",
        "text-xs font-medium rounded-full",
        "border whitespace-nowrap",
        className,
      ].join(" ")}
      style={{
        backgroundColor: bg,
        color: text,
        borderColor: border,
      }}
    >
      {children}
    </span>
  );
}

/** Maps analysis status string to a Badge with dot indicator */
export function StatusBadge({ status }: { status: string }) {
  const variant: BadgeVariant =
    status === "completed" ? "success"
    : status === "running"  ? "info"
    : status === "failed"   ? "danger"
    : status === "pending"  ? "warning"
    : "neutral";

  return (
    <Badge variant={variant}>
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          backgroundColor: "currentColor",
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      {status}
    </Badge>
  );
}
