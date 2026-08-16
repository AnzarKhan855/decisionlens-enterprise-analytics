"use client";

import React from "react";

interface ChartCardProps {
  title: string;
  subtitle?: string;
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyMessage?: string;
  emptyDescription?: string;
  emptyIcon?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
  footer?: React.ReactNode;
  header?: React.ReactNode;
}

export default function ChartCard({
  title,
  subtitle,
  loading = false,
  error = null,
  empty = false,
  emptyMessage,
  emptyDescription,
  emptyIcon,
  className = "",
  children,
  actions,
  footer,
  header,
}: ChartCardProps) {
  if (loading) {
    return (
      <div className={`chart-card ${className}`}>
        <div className="chart-card-header">
          <div>
            <h3 className="chart-card-title">{title}</h3>
            {subtitle && <p className="chart-card-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="chart-card-actions">{actions}</div>}
        </div>
        <div className="chart-skeleton" aria-hidden="true">
          <div className="chart-skeleton-bar" />
          <div className="chart-skeleton-bar chart-skeleton-bar--short" />
          <div className="chart-skeleton-bar" />
          <div className="chart-skeleton-bar chart-skeleton-bar--medium" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`chart-card chart-card--error ${className}`}>
        <div className="chart-card-header">
          <div>
            <h3 className="chart-card-title">{title}</h3>
            {subtitle && <p className="chart-card-subtitle">{subtitle}</p>}
          </div>
        </div>
        <div className="chart-error">
          <div className="chart-error-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <p className="chart-error-text">{error}</p>
        </div>
      </div>
    );
  }

  if (empty) {
    return (
      <div className={`chart-card ${className}`}>
        {header || (
          <div className="chart-card-header">
            <div>
              <h3 className="chart-card-title">{title}</h3>
              {subtitle && <p className="chart-card-subtitle">{subtitle}</p>}
            </div>
            {actions && <div className="chart-card-actions">{actions}</div>}
          </div>
        )}
        <div className="chart-empty">
          {emptyIcon && <div className="chart-empty-icon">{emptyIcon}</div>}
          {emptyMessage && <p className="chart-empty-message">{emptyMessage}</p>}
          {emptyDescription && <p className="chart-empty-description">{emptyDescription}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className={`chart-card ${className}`}>
      {header || (
        <div className="chart-card-header">
          <div>
            <h3 className="chart-card-title">{title}</h3>
            {subtitle && <p className="chart-card-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="chart-card-actions">{actions}</div>}
        </div>
      )}

      <div className="chart-canvas">
        {children}
      </div>

      {footer && (
        <div className="chart-footer">
          {footer}
        </div>
      )}
    </div>
  );
}
