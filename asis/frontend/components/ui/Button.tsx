"use client";

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

type ButtonVariant = "primary" | "ghost" | "outline" | "danger";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: [
    "bg-[var(--accent)] text-white",
    "hover:bg-[var(--accent-hover)]",
    "disabled:bg-[var(--accent-dim)] disabled:text-[var(--text-tertiary)]",
    "shadow-sm",
  ].join(" "),
  ghost: [
    "bg-transparent text-[var(--text-secondary)]",
    "hover:bg-[var(--bg-elevated)] hover:text-[var(--text-primary)]",
    "disabled:text-[var(--text-tertiary)]",
  ].join(" "),
  outline: [
    "bg-transparent text-[var(--text-primary)]",
    "border border-[var(--border)]",
    "hover:border-[var(--border-hover)] hover:bg-[var(--bg-elevated)]",
    "disabled:text-[var(--text-tertiary)] disabled:border-[var(--border)]",
  ].join(" "),
  danger: [
    "bg-[var(--danger-dim)] text-[var(--danger)]",
    "border border-[var(--danger)]/30",
    "hover:bg-[var(--danger)]/20 hover:border-[var(--danger)]/50",
    "disabled:opacity-40",
  ].join(" "),
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-7 px-3 text-xs gap-1.5 rounded-[var(--radius-sm)]",
  md: "h-9 px-4 text-sm gap-2 rounded-[var(--radius-md)]",
  lg: "h-11 px-6 text-sm gap-2 rounded-[var(--radius-md)]",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      className = "",
      ...rest
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={[
          "inline-flex items-center justify-center font-medium",
          "transition-colors",
          "cursor-pointer disabled:cursor-not-allowed",
          "select-none focus-visible:outline-none focus-visible:ring-2",
          "focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2",
          "focus-visible:ring-offset-[var(--bg-base)]",
          variantStyles[variant],
          sizeStyles[size],
          className,
        ].join(" ")}
        style={{ transitionDuration: "var(--transition-fast)" }}
        {...rest}
      >
        {loading ? (
          <span
            className="shrink-0"
            style={{
              width: size === "sm" ? 12 : 14,
              height: size === "sm" ? 12 : 14,
              borderRadius: "50%",
              border: "2px solid transparent",
              borderTopColor: "currentColor",
              animation: "spin 0.7s linear infinite",
              display: "inline-block",
            }}
          />
        ) : (
          leftIcon && <span className="shrink-0">{leftIcon}</span>
        )}
        {children}
        {rightIcon && !loading && (
          <span className="shrink-0">{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
