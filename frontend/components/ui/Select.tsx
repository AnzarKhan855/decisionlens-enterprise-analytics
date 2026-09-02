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
  const [highlightedIndex, setHighlightedIndex] = useState<number>(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const reactId = useId();
  const buttonId = `select-${name || "default"}-${reactId}`;
  const listboxId = `${buttonId}-listbox`;

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

  useEffect(() => {
    if (isOpen) {
      const idx = filteredOptions.findIndex((opt) => opt.value === value);
      setHighlightedIndex(idx >= 0 ? idx : 0);
    } else {
      setHighlightedIndex(-1);
    }
  }, [isOpen, filteredOptions, value]);

  const handleSelect = (optionValue: string) => {
    onChange?.(optionValue);
    setIsOpen(false);
    setSearch("");
    buttonRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;

    if (!isOpen) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((prev) => (filteredOptions.length > 0 ? (prev + 1) % filteredOptions.length : -1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((prev) => (filteredOptions.length > 0 ? (prev - 1 + filteredOptions.length) % filteredOptions.length : -1));
        break;
      case "Enter":
      case " ":
        if (!searchable || e.target !== inputRef.current) {
          e.preventDefault();
          if (highlightedIndex >= 0 && highlightedIndex < filteredOptions.length) {
            const opt = filteredOptions[highlightedIndex];
            if (!opt.disabled) {
              handleSelect(opt.value);
            }
          }
        }
        break;
      case "Escape":
        e.preventDefault();
        setIsOpen(false);
        setSearch("");
        buttonRef.current?.focus();
        break;
      case "Tab":
        setIsOpen(false);
        setSearch("");
        break;
    }
  };

  return (
    <div className={`w-full ${className}`} onKeyDown={handleKeyDown}>
      {label && (
        <label htmlFor={buttonId} className="block text-xs font-semibold text-text-secondary mb-1.5">
          {label}
        </label>
      )}
      <div ref={containerRef} className="relative">
        <button
          ref={buttonRef}
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
          aria-controls={isOpen ? listboxId : undefined}
        >
          <span className={selectedOption ? "text-text-primary font-medium" : "text-text-muted"}>
            {selectedOption?.label || placeholder}
          </span>
          <ChevronDown className={`w-4 h-4 text-text-muted transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} aria-hidden="true" />
        </button>

        {isOpen && (
          <div
            id={listboxId}
            className="absolute z-50 w-full mt-1 bg-surface border border-border-color rounded-xl shadow-lg shadow-slate-900/10 overflow-hidden animate-scale-in"
            role="listbox"
            aria-labelledby={label ? buttonId : undefined}
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
            <div className="max-h-60 overflow-y-auto p-1.5 space-y-0.5">
              {filteredOptions.length === 0 ? (
                <div className="px-3 py-2 text-xs text-text-muted text-center">
                  No options found
                </div>
              ) : (
                filteredOptions.map((option, index) => {
                  const isSelected = option.value === value;
                  const isHighlighted = highlightedIndex === index;
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
                        ${isHighlighted && !isSelected ? "bg-surface-muted/80 text-text-primary ring-1 ring-primary-500/30" : ""}
                        ${option.disabled ? "opacity-40 cursor-not-allowed" : ""}
                      `}
                      role="option"
                      aria-selected={isSelected}
                    >
                      <span>{option.label}</span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />}
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
