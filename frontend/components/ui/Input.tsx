"use client";

import React, { forwardRef, useState } from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
  floatingLabel?: boolean;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, icon, iconPosition = "left", floatingLabel = false, className = "", id, ...props }, ref) => {
    const [focused, setFocused] = useState(false);
    const [hasValue, setHasValue] = useState(false);
    const inputId = id || `input-${label?.replace(/\s+/g, "-").toLowerCase() || Math.random().toString(36).slice(2)}`;
    const errorId = `${inputId}-error`;
    const hintId = `${inputId}-hint`;

    const showFloatingLabel = floatingLabel && (focused || hasValue || props.value || props.defaultValue);

    const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
      setFocused(true);
      setHasValue(!!e.target.value);
      props.onFocus?.(e);
    };

    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      setFocused(false);
      setHasValue(!!e.target.value);
      props.onBlur?.(e);
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setHasValue(!!e.target.value);
      props.onChange?.(e);
    };

    const iconLeft = iconPosition === "left" && icon;
    const iconRight = iconPosition === "right" && icon;

    return (
      <div className="w-full">
        {!floatingLabel && label && (
          <label htmlFor={inputId} className="block text-xs font-semibold text-text-secondary mb-1.5">
            {label}
          </label>
        )}
        <div className="relative">
          {iconLeft && (
            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" aria-hidden="true">
              {iconLeft}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            onFocus={handleFocus}
            onBlur={handleBlur}
            onChange={handleChange}
            aria-invalid={!!error}
            aria-describedby={error ? errorId : hint ? hintId : undefined}
            className={`
              w-full rounded-xl border text-sm transition-all outline-none
              ${floatingLabel ? "pt-5 pb-2" : "py-2.5"}
              ${iconLeft ? "pl-10" : "pl-4"}
              ${iconRight ? "pr-10" : "pr-4"}
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
          {iconRight && (
            <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" aria-hidden="true">
              {iconRight}
            </span>
          )}
          {floatingLabel && label && (
            <label
              htmlFor={inputId}
              className={`
                absolute left-4 transition-all duration-200 pointer-events-none origin-left
                ${showFloatingLabel ? "top-1.5 text-[10px] text-primary-600 font-semibold" : "top-1/2 -translate-y-1/2 text-sm text-text-muted"}
                ${iconLeft ? "left-10" : "left-4"}
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

Input.displayName = "Input";

export default Input;
