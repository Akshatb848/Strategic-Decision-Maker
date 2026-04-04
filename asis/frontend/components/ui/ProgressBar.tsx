"use client";

interface ProgressBarProps {
  /** 0–100 */
  width: number;
  color?: string;
  height?: number;
  className?: string;
  animated?: boolean;
  label?: string;
}

export function ProgressBar({
  width,
  color = "var(--accent)",
  height = 4,
  className = "",
  animated = true,
  label,
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, width));

  return (
    <div
      className={className}
      style={{
        width: "100%",
        height,
        borderRadius: 999,
        backgroundColor: "var(--bg-overlay)",
        overflow: "hidden",
      }}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
    >
      <div
        style={{
          width: `${pct}%`,
          height: "100%",
          backgroundColor: pct === 100 ? "var(--success)" : color,
          borderRadius: 999,
          transition: animated ? "width 0.4s ease-out" : undefined,
        }}
      />
    </div>
  );
}
