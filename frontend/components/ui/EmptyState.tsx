"use client";

import React from "react";

interface EmptyStateProps {
  icon?: React.ReactNode;
  illustration?: React.ReactNode;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  variant?: "centered" | "compact";
  className?: string;
}

export default function EmptyState({
  icon,
  illustration,
  title,
  description,
  actions,
  variant = "centered",
  className = "",
}: EmptyStateProps) {
  if (variant === "compact") {
    return (
      <div
        className={`flex flex-col items-center justify-center text-center py-8 px-6 ${className}`}
        role="status"
      >
        {illustration ? (
          <div className="mb-3">{illustration}</div>
        ) : icon ? (
          <div className="mb-3 p-2.5 bg-surface-muted text-text-muted rounded-2xl border border-border-color">
            {icon}
          </div>
        ) : null}
        <h3 className="text-sm font-bold text-text-primary mb-0.5">{title}</h3>
        {description && (
          <p className="text-xs text-text-muted max-w-sm leading-relaxed mb-3">
            {description}
          </p>
        )}
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    );
  }

  return (
    <div
      className={`flex flex-col items-center justify-center text-center py-16 px-6 ${className}`}
      role="status"
    >
      {illustration ? (
        <div className="mb-6">{illustration}</div>
      ) : icon ? (
        <div className="mb-5 p-4 bg-surface-muted text-text-muted rounded-2xl border border-border-color">
          {icon}
        </div>
      ) : null}
      <h3 className="text-base font-bold text-text-primary mb-1.5">{title}</h3>
      {description && (
        <p className="text-sm text-text-muted max-w-md leading-relaxed mb-6">
          {description}
        </p>
      )}
      {actions && <div className="flex items-center justify-center gap-3">{actions}</div>}
    </div>
  );
}
