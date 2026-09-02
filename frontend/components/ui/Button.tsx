"use client";

import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger" | "success" | "link";
  size?: "xs" | "sm" | "md" | "lg";
  loading?: boolean;
  loadingText?: string;
  icon?: React.ReactNode;
  fullWidth?: boolean;
}

export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  loadingText,
  icon,
  fullWidth = false,
  children,
  className = "",
  disabled,
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 font-semibold rounded-xl transition-all focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none select-none";

  const variants = {
    primary:
      "bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800 shadow-sm shadow-primary-600/20 hover:shadow-md active:shadow-sm active:scale-[0.98] focus-visible:ring-primary-500",
    secondary:
      "bg-surface text-text-secondary border border-border-color hover:bg-surface-muted hover:border-border-strong active:bg-surface-muted active:scale-[0.98] focus-visible:ring-slate-400",
    outline:
      "bg-transparent text-primary-600 border border-primary-200 hover:bg-primary-50 active:bg-primary-100 active:scale-[0.98] focus-visible:ring-primary-500",
    ghost:
      "bg-transparent text-text-secondary hover:bg-surface-muted active:bg-border-color active:scale-[0.98] focus-visible:ring-slate-400",
    danger:
      "bg-error-600 text-white hover:bg-error-700 active:bg-error-800 shadow-sm shadow-error-600/20 hover:shadow-md active:shadow-sm active:scale-[0.98] focus-visible:ring-error-500",
    success:
      "bg-success-600 text-white hover:bg-success-700 active:bg-success-800 shadow-sm shadow-success-600/20 hover:shadow-md active:shadow-sm active:scale-[0.98] focus-visible:ring-emerald-500",
    link:
      "bg-transparent text-primary-600 hover:text-primary-700 underline underline-offset-4 decoration-primary-300 hover:decoration-primary-500 active:text-primary-800 focus-visible:ring-primary-500 p-0 h-auto",
  };

  const sizes = {
    xs: "px-2.5 py-1.5 text-xs gap-1.5 h-8",
    sm: "px-3 py-2 text-xs gap-1.5 h-9",
    md: "px-4 py-2.5 text-sm gap-2 h-10",
    lg: "px-6 py-3 text-sm gap-2.5 h-11",
  };

  const spinnerSizes = {
    xs: "w-3 h-3 border-[1.5px]",
    sm: "w-3.5 h-3.5 border-2",
    md: "w-4 h-4 border-2",
    lg: "w-5 h-5 border-2.5",
  };

  const isLink = variant === "link";

  return (
    <button
      className={`
        ${base}
        ${variants[variant]}
        ${sizes[size]}
        ${fullWidth && !isLink ? "w-full" : ""}
        ${loading && !isLink ? "cursor-wait" : ""}
        ${className}
      `}
      disabled={disabled || loading}
      aria-busy={loading ? "true" : undefined}
      {...props}
    >
      {loading && !isLink ? (
        <span
          className={`
            ${spinnerSizes[size]}
            border-current border-t-transparent rounded-full animate-spin
          `}
          aria-hidden="true"
        />
      ) : icon ? (
        <span className="shrink-0 flex items-center" aria-hidden="true">{icon}</span>
      ) : null}
      {loading && loadingText ? loadingText : children}
    </button>
  );
}
