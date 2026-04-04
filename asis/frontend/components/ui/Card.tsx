"use client";

import { type HTMLAttributes, type ReactNode, forwardRef } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  padding?: "none" | "sm" | "md" | "lg";
  hover?: boolean;
  elevated?: boolean;
}

const paddingMap = {
  none: "p-0",
  sm: "p-3",
  md: "p-5",
  lg: "p-6",
};

export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      padding = "md",
      hover = false,
      elevated = false,
      className = "",
      style,
      ...rest
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={[
          "rounded-[var(--radius-lg)]",
          paddingMap[padding],
          className,
        ].join(" ")}
        style={{
          backgroundColor: elevated ? "var(--bg-elevated)" : "var(--bg-surface)",
          border: "1px solid var(--border)",
          transition: hover
            ? "border-color var(--transition-base), box-shadow var(--transition-base), background-color var(--transition-base)"
            : undefined,
          ...style,
        }}
        onMouseEnter={
          hover
            ? (e) => {
                const el = e.currentTarget as HTMLDivElement;
                el.style.borderColor = "var(--border-hover)";
                el.style.boxShadow = "var(--shadow-md)";
              }
            : undefined
        }
        onMouseLeave={
          hover
            ? (e) => {
                const el = e.currentTarget as HTMLDivElement;
                el.style.borderColor = "var(--border)";
                el.style.boxShadow = "";
              }
            : undefined
        }
        {...rest}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";

export function CardHeader({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={["flex items-center justify-between mb-4", className].join(" ")}>
      {children}
    </div>
  );
}

export function CardTitle({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <h3
      className={["text-sm font-semibold", className].join(" ")}
      style={{ color: "var(--text-primary)" }}
    >
      {children}
    </h3>
  );
}
