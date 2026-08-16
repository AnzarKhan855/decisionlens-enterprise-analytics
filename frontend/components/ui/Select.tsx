"use client";

import React, { useState, useRef, useEffect, useId } from "react";
import { ChevronDown, Check } from "lucide-react";

interface Option {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectProps {
  label?: string;
  placeholder?: string;
  options: Option[];
  value?: string;
  onChange?: (value: string) => void;
  error?: string;
  disabled?: boolean;
  searchable?: boolean;
  className?: string;
  name?: string;
}

export default function Select({
  label,
  placeholder = "Select an option",
  options,
  value,
  onChange,
  error,
  disabled = false,
  searchable = false,
  className = "",
  name,
}: SelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const reactId = useId();
  const buttonId = `select-${name || "default"}-${reactId}`;

  const selectedOption = options.find((opt) => opt.value === value);

  const filteredOptions = searchable
    ? options.filter((opt) => opt.label.toLowerCase().includes(search.toLowerCase()))
    : options;

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setSearch("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (isOpen && searchable && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen, searchable]);

  const handleSelect = (optionValue: string) => {
    onChange?.(optionValue);
    setIsOpen(false);
    setSearch("");
  };

  return (
    <div className={`w-full ${className}`}>
      {label && (
        <label htmlFor={buttonId} className="block text-xs font-semibold text-text-secondary mb-1.5">
          {label}
        </label>
      )}
      <div ref={containerRef} className="relative">
        <button
          id={buttonId}
          type="button"
          disabled={disabled}
          onClick={() => !disabled && setIsOpen(!isOpen)}
          className={`
            w-full flex items-center justify-between gap-2 px-4 py-2.5 rounded-xl border text-sm
            transition-all outline-none cursor-pointer
            ${error ? "border-error-500 bg-error-50/50" : "border-border-color bg-surface-muted/50 hover:border-border-strong"}
            ${disabled ? "opacity-50 cursor-not-allowed" : ""}
            focus-visible:ring-2 focus-visible:ring-primary-500/20 focus-visible:border-primary-500
          `}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
        >
          <span className={selectedOption ? "text-text-primary" : "text-text-muted"}>
            {selectedOption?.label || placeholder}
          </span>
          <ChevronDown className={`w-4 h-4 text-text-muted transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} aria-hidden="true" />
        </button>

        {isOpen && (
          <div
            className="absolute z-50 w-full mt-1 bg-surface border border-border-color rounded-xl shadow-lg shadow-slate-900/10 overflow-hidden"
            role="listbox"
          >
            {searchable && (
              <div className="p-2 border-b border-border-color">
                <input
                  ref={inputRef}
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search..."
                  aria-label="Search options"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border-color bg-surface-muted outline-none focus:border-primary-500"
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            )}
            <div className="max-h-60 overflow-y-auto p-1.5">
              {filteredOptions.length === 0 ? (
                <div className="px-3 py-2 text-xs text-text-muted text-center">
                  No options found
                </div>
              ) : (
                filteredOptions.map((option) => {
                  const isSelected = option.value === value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      disabled={option.disabled}
                      onClick={() => handleSelect(option.value)}
                      className={`
                        w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-xs text-left
                        transition-colors cursor-pointer
                        ${isSelected ? "bg-primary-50 text-primary-700 font-semibold" : "text-text-secondary hover:bg-surface-muted"}
                        ${option.disabled ? "opacity-40 cursor-not-allowed" : ""}
                      `}
                      role="option"
                      aria-selected={isSelected}
                    >
                      <span>{option.label}</span>
                      {isSelected && <Check className="w-3.5 h-3.5" aria-hidden="true" />}
                    </button>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>
      {error && (
        <p className="mt-1.5 text-[11px] text-error-600 font-medium" role="alert">
          {error}
        </p>
      )}
      {name && <input type="hidden" name={name} value={value || ""} />}
    </div>
  );
}
