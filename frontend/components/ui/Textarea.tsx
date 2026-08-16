"use client";

import React, { forwardRef, useState, useCallback } from "react";

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
  floatingLabel?: boolean;
  autoResize?: boolean;
  maxRows?: number;
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      label,
      error,
      hint,
      floatingLabel = false,
      autoResize = false,
      maxRows = 8,
      className = "",
      id,
      rows = 4,
      onFocus,
      onBlur,
      onChange,
      value,
      defaultValue,
      ...props
    },
    ref
  ) => {
    const [focused, setFocused] = useState(false);
    const [hasValue, setHasValue] = useState(false);
    const [internalRows, setInternalRows] = useState(rows);

    const textareaId = id || `textarea-${label?.replace(/\s+/g, "-").toLowerCase() || Math.random().toString(36).slice(2)}`;
    const errorId = `${textareaId}-error`;
    const hintId = `${textareaId}-hint`;

    const showFloatingLabel = floatingLabel && (focused || hasValue || value || defaultValue);

    const handleFocus = useCallback(
      (e: React.FocusEvent<HTMLTextAreaElement>) => {
        setFocused(true);
        setHasValue(!!e.target.value);
        onFocus?.(e);
      },
      [onFocus]
    );

    const handleBlur = useCallback(
      (e: React.FocusEvent<HTMLTextAreaElement>) => {
        setFocused(false);
        setHasValue(!!e.target.value);
        onBlur?.(e);
      },
      [onBlur]
    );

    const handleChange = useCallback(
      (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setHasValue(!!e.target.value);
        if (autoResize) {
          e.target.style.height = "auto";
          const lineHeight = 1.5;
          const maxHeight = maxRows * 1.5 * 16;
          e.target.style.height = `${Math.min(e.target.scrollHeight, maxHeight)}px`;
        }
        onChange?.(e);
      },
      [autoResize, maxRows, onChange]
    );

    React.useImperativeHandle(
      ref,
      () => document.getElementById(textareaId) as HTMLTextAreaElement
    );

    return (
      <div className="w-full relative">
        {!floatingLabel && label && (
          <label htmlFor={textareaId} className="block text-xs font-semibold text-text-secondary mb-1.5">
            {label}
          </label>
        )}
        <div className="relative">
          <textarea
            ref={ref}
            id={textareaId}
            rows={autoResize ? 1 : rows}
            onFocus={handleFocus}
            onBlur={handleBlur}
            onChange={handleChange}
            aria-invalid={!!error}
            aria-describedby={error ? errorId : hint ? hintId : undefined}
            className={`
              w-full rounded-xl border text-sm transition-all outline-none resize-none
              ${floatingLabel ? "pt-5 pb-2" : "py-2.5"}
              px-4
              ${error
                ? "border-error-500 focus:border-error-500 focus:ring-2 focus:ring-error-500/20 bg-error-50/50"
                : "border-border-color focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 bg-surface-muted/50"
              }
              text-text-primary placeholder:text-text-muted
              disabled:opacity-50 disabled:cursor-not-allowed
              ${className}
            `}
            {...props}
          />
          {floatingLabel && label && (
            <label
              htmlFor={textareaId}
              className={`
                absolute left-4 transition-all duration-200 pointer-events-none origin-left
                ${showFloatingLabel ? "top-1.5 text-[10px] text-primary-600 font-semibold" : "top-3 text-sm text-text-muted"}
              `}
            >
              {label}
            </label>
          )}
        </div>
        {error && (
          <p id={errorId} className="mt-1.5 text-[11px] text-error-600 font-medium" role="alert">
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={hintId} className="mt-1.5 text-[11px] text-text-muted">
            {hint}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";

export default Textarea;
