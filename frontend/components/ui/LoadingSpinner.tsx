"use client";

import React from "react";

interface LoadingSpinnerProps {
  label?: string;
  sublabel?: string;
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  overlay?: boolean;
  fullScreen?: boolean;
}

export default function LoadingSpinner({
  label = "Loading...",
  sublabel,
  size = "md",
  overlay = false,
  fullScreen = false,
}: LoadingSpinnerProps) {
  const spinnerSizes = {
    xs: "w-4 h-4 border-[1.5px]",
    sm: "w-5 h-5 border-2",
    md: "w-8 h-8 border-2",
    lg: "w-10 h-10 border-[3px]",
    xl: "w-14 h-14 border-4",
  };

  const textSizes = {
    xs: "text-xs",
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base",
    xl: "text-lg",
  };

  const content = (
    <div className="flex flex-col items-center justify-center gap-3">
      <div
        className={`${spinnerSizes[size]} border-primary-600 border-t-transparent rounded-full animate-spin`}
        role="status"
        aria-live="polite"
        aria-label={label}
      />
      <div className="text-center space-y-1">
        <p className={`font-semibold text-text-primary ${textSizes[size]}`}>{label}</p>
        {sublabel && (
          <p className="text-xs text-text-muted">{sublabel}</p>
        )}
      </div>
    </div>
  );

  if (overlay) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-background/40 backdrop-blur-sm"
        role="status"
        aria-live="polite"
        aria-label={label}
      >
        <div className="bg-surface rounded-2xl shadow-lg p-8 animate-scale-in">
          {content}
        </div>
      </div>
    );
  }

  if (fullScreen) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-surface-muted"
        role="status"
        aria-live="polite"
        aria-label={label}
      >
        {content}
      </div>
    );
  }

  return (
    <div
      className="flex items-center justify-center"
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      {content}
    </div>
  );
}
