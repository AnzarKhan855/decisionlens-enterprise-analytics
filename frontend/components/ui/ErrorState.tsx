"use client";

import React from "react";

type Severity = "error" | "warning" | "info";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  retryLabel?: string;
  severity?: Severity;
  icon?: React.ReactNode;
}

const severityConfig: Record<Severity, { bg: string; text: string; border: string; shadow: string }> = {
  error: {
    bg: "bg-error-50",
    text: "text-error-600",
    border: "border-error-100",
    shadow: "shadow-error",
  },
  warning: {
    bg: "bg-warning-50",
    text: "text-warning-600",
    border: "border-warning-100",
    shadow: "shadow-warning",
  },
  info: {
    bg: "bg-info-50",
    text: "text-info-600",
    border: "border-info-100",
    shadow: "shadow-info",
  },
};

const defaultIcons: Record<Severity, React.ReactNode> = {
  error: (
    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
    </svg>
  ),
  warning: (
    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
    </svg>
  ),
  info: (
    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
    </svg>
  ),
};

export default function ErrorState({
  title = "Something went wrong",
  description = "We encountered an unexpected error. Please try again.",
  onRetry,
  retryLabel = "Try Again",
  severity = "error",
  icon,
}: ErrorStateProps) {
  const config = severityConfig[severity];

  return (
    <div
      className="flex flex-col items-center justify-center text-center py-16 px-6"
      role="alert"
      aria-live="assertive"
    >
      <div className={`mb-5 p-3.5 rounded-2xl border ${config.bg} ${config.text} ${config.border} shadow-md`}>
        {icon ?? defaultIcons[severity]}
      </div>
      <h3 className="text-base font-bold text-text-primary mb-1.5">{title}</h3>
      <p className="text-sm text-text-muted max-w-md leading-relaxed mb-5">
        {description}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className={`
            px-5 py-2.5 text-white text-sm font-semibold rounded-xl
            transition-all shadow-sm hover:shadow-md active:scale-[0.97]
            focus-visible:ring-2 focus-visible:ring-offset-2
            ${severity === "error" ? "bg-error-600 hover:bg-error-700 focus-visible:ring-error-500 shadow-error" : ""}
            ${severity === "warning" ? "bg-warning-600 hover:bg-warning-700 focus-visible:ring-amber-500 shadow-warning" : ""}
            ${severity === "info"    ? "bg-info-600 hover:bg-info-700 focus-visible:ring-info-500 shadow-info" : ""}
          `}
        >
          {retryLabel}
        </button>
      )}
    </div>
  );
}
