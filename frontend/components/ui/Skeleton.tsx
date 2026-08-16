"use client";

import React from "react";

type SkeletonVariant = "text" | "text-lg" | "circular" | "rectangular" | "card" | "table-row" | "avatar" | "chart";

interface SkeletonProps {
  className?: string;
  variant?: SkeletonVariant;
  width?: string | number;
  height?: string | number;
  lines?: number;
}

export default function Skeleton({
  className = "",
  variant = "rectangular",
  width,
  height,
  lines = 3,
}: SkeletonProps) {
  const base = "skeleton-shimmer bg-border-color";

  const variantClasses: Record<SkeletonVariant, string> = {
    text: `h-3 rounded-md w-full`,
    "text-lg": `h-4 rounded-md w-full`,
    circular: "rounded-full",
    rectangular: "rounded-xl",
    card: "h-48 rounded-2xl",
    "table-row": "h-14 rounded-lg",
    avatar: "rounded-full",
    chart: "h-60 rounded-xl",
  };

  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === "number" ? `${width}px` : width;
  if (height) style.height = typeof height === "number" ? `${height}px` : height;

  if (variant === "text" && lines > 1) {
    return (
      <div className={`space-y-2.5 ${className}`} aria-hidden="true">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={`${base} ${variantClasses.text}`}
            style={{
              width: i === lines - 1 ? "70%" : "100%",
              ...style,
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`${base} ${variantClasses[variant]} ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}
