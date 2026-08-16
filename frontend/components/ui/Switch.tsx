"use client";

import React, { useState, useCallback } from "react";

interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange" | "type"> {
  label?: string;
  description?: string;
  onChange?: (checked: boolean) => void;
}

export default function Switch({
  label,
  description,
  onChange,
  disabled = false,
  checked: controlledChecked,
  className = "",
  id,
  ...props
}: SwitchProps) {
  const [internalChecked, setInternalChecked] = useState(false);
  const isControlled = controlledChecked !== undefined;
  const checked = isControlled ? controlledChecked : internalChecked;

  const switchId = id || `switch-${label?.replace(/\s+/g, "-").toLowerCase() || Math.random().toString(36).slice(2)}`;
  const descriptionId = `${switchId}-description`;

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newChecked = e.target.checked;
      if (!isControlled) {
        setInternalChecked(newChecked);
      }
      onChange?.(newChecked);
    },
    [isControlled, onChange]
  );

  return (
    <div className={`flex items-start gap-3 ${className}`}>
      <div className="relative flex items-center pt-0.5">
        <input
          type="checkbox"
          role="switch"
          id={switchId}
          checked={checked}
          onChange={handleChange}
          disabled={disabled}
          aria-describedby={description ? descriptionId : undefined}
          className="peer sr-only"
          {...props}
        />
        <label
          htmlFor={switchId}
          className={`
            block w-10 h-6 rounded-full cursor-pointer
            bg-border-color
            peer-checked:bg-primary-500
            peer-focus-visible:ring-2 peer-focus-visible:ring-primary-500 peer-focus-visible:ring-offset-2
            peer-disabled:opacity-50 peer-disabled:cursor-not-allowed
            transition-colors duration-200
          `}
          aria-hidden="true"
        >
          <span
            className={`
              block w-4 h-4 rounded-full bg-white shadow-sm
              transform transition-transform duration-200 ease-out
              ${checked ? "translate-x-5" : "translate-x-1"}
              peer-disabled:bg-text-muted
              mt-1
            `}
          />
        </label>
      </div>
      {(label || description) && (
        <div className="flex flex-col">
          {label && (
            <label htmlFor={switchId} className={`text-sm font-medium text-text-primary ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}>
              {label}
            </label>
          )}
          {description && (
            <p id={descriptionId} className="text-xs text-text-muted mt-0.5">
              {description}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
