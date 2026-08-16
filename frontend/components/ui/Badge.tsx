"use client";

import React from "react";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "info" | "neutral";
  size?: "sm" | "md";
  dot?: boolean;
  pill?: boolean;
  className?: string;
}

const variantClasses = {
  default: "bg-primary-50 text-primary-700 border border-primary-200",
  success: "bg-success-50 text-success-700 border border-success-200",
  warning: "bg-warning-50 text-warning-700 border border-warning-200",
  error: "bg-error-50 text-error-700 border border-error-200",
  info: "bg-info-50 text-info-700 border border-info-200",
  neutral: "bg-surface-muted text-text-secondary border border-border-color",
};

const dotColors = {
  default: "bg-primary-500",
  success: "bg-success-500",
  warning: "bg-warning-500",
  error: "bg-error-500",
  info: "bg-info-500",
  neutral: "bg-foreground",
};

const sizeClasses = {
  sm: "px-2 py-0.5 text-[10px]",
  md: "px-2.5 py-1 text-xs",
};

export default function Badge({
  children,
  variant = "default",
  size = "sm",
  dot = false,
  pill = false,
  className = "",
}: BadgeProps) {
  return (
    <span
      className={`
        inline-flex items-center font-bold gap-1.5
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${pill ? "rounded-full" : "rounded-lg"}
        ${className}
      `}
      aria-label={dot ? `Status: ${children}` : undefined}
    >
      {dot && (
        <span
          className={`h-2 w-2 rounded-full shrink-0 ${dotColors[variant]}`}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}
