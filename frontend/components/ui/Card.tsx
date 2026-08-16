"use client";

import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
  variant?: "default" | "elevated" | "outlined" | "hoverable" | "clickable" | "subtle" | "gradient";
  onClick?: () => void;
  headerGradient?: "primary" | "success" | "warning" | "info";
  header?: React.ReactNode;
  footer?: React.ReactNode;
  as?: "div" | "article" | "section";
}

const paddingClasses = {
  none: "",
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

const variantClasses = {
  default: "premium-card",
  elevated: "premium-card shadow-lg",
  outlined: "bg-transparent border-2 border-border-color",
  hoverable: "premium-card card-hover cursor-default",
  clickable: "premium-card cursor-pointer active:scale-[0.98]",
  subtle: "bg-surface-muted border border-border-color rounded-2xl shadow-sm",
  gradient: "",
};

const gradientClasses = {
  primary: "bg-gradient-to-br from-primary-500 to-primary-700 text-white",
  success: "bg-gradient-to-br from-success-500 to-success-700 text-white",
  warning: "bg-gradient-to-br from-warning-500 to-warning-600 text-white",
  info: "bg-gradient-to-br from-info-500 to-info-600 text-white",
};

export default function Card({
  children,
  className = "",
  padding = "md",
  variant = "default",
  onClick,
  headerGradient,
  header,
  footer,
  as = "div",
}: CardProps) {
  const isGradient = variant === "gradient";
  const isSubtle = variant === "subtle";
  const Component = onClick || variant === "clickable" ? "button" : as;

  const baseClasses = [
    "rounded-2xl",
    "transition-all",
    "duration-200",
    paddingClasses[padding],
    isGradient ? gradientClasses[headerGradient ?? "primary"] : variantClasses[variant],
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const headerBorder = isGradient ? "border-foreground/20" : isSubtle ? "border-border-color" : "border-border-light";
  const headerBg = isGradient ? "" : isSubtle ? "bg-surface-muted/60" : "bg-surface-muted/40";

  return (
    <Component
      type={onClick ? "button" : undefined}
      className={baseClasses}
      onClick={onClick}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      {header && (
        <div
          className={`
            px-5 py-4 border-b
            ${headerBorder}
            ${headerBg}
            ${isGradient ? "" : ""}
          `}
        >
          {typeof header === "string" ? (
            <h3 className="text-sm font-bold text-text-primary tracking-tight">{header}</h3>
          ) : (
            header
          )}
        </div>
      )}
      <div className={footer ? "flex-1" : ""}>{children}</div>
      {footer && (
        <div
          className={`
            px-5 py-3.5 border-t
            ${headerBorder}
            ${isGradient ? "" : "bg-surface-muted/30"}
          `}
        >
          {footer}
        </div>
      )}
    </Component>
  );
}
