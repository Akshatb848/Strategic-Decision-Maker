"use client";

type DotStatus = "idle" | "running" | "done" | "error" | "queued";

interface StatusDotProps {
  status: DotStatus;
  size?: number;
}

const colorMap: Record<DotStatus, string> = {
  idle:    "var(--text-tertiary)",
  running: "var(--accent)",
  done:    "var(--success)",
  error:   "var(--danger)",
  queued:  "var(--warning)",
};

const glowMap: Record<DotStatus, string | undefined> = {
  idle:    undefined,
  running: "0 0 0 3px rgba(124,58,237,0.25)",
  done:    undefined,
  error:   "0 0 0 3px rgba(239,68,68,0.2)",
  queued:  undefined,
};

export function StatusDot({ status, size = 8 }: StatusDotProps) {
  const color = colorMap[status];
  const glow = glowMap[status];
  const isPulsing = status === "running";

  return (
    <span
      role="status"
      aria-label={`Status: ${status}`}
      style={{
        display: "inline-block",
        width: size,
        height: size,
        borderRadius: "50%",
        backgroundColor: color,
        flexShrink: 0,
        boxShadow: glow,
        animation: isPulsing ? "pulse-dot 1.6s ease-in-out infinite" : undefined,
      }}
    />
  );
}
