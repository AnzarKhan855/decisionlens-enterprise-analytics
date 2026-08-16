"use client";

import React from "react";

export default function Loading() {
  return (
    <div className="min-h-screen bg-background" aria-label="Loading" role="status">
      {/* Header skeleton */}
      <div className="h-16 bg-surface border-b border-border-color px-4 lg:px-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-border-color skeleton-shimmer" />
          <div className="space-y-2">
            <div className="w-32 h-3 rounded bg-border-color skeleton-shimmer" />
            <div className="w-24 h-2 rounded bg-surface-muted skeleton-shimmer" />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-lg bg-border-color skeleton-shimmer" />
          <div className="w-9 h-9 rounded-lg bg-border-color skeleton-shimmer hidden sm:flex" />
          <div className="w-8 h-8 rounded-full bg-border-color skeleton-shimmer" />
        </div>
      </div>

      <div className="flex h-[calc(100vh-4rem)]">
        {/* Sidebar skeleton */}
        <div className="hidden lg:block w-64 border-r border-border-color bg-background p-4 space-y-4">
          <div className="space-y-3">
            <div className="w-8 h-8 rounded-xl bg-surface-muted skeleton-shimmer" />
            <div className="w-24 h-3 rounded bg-surface-muted skeleton-shimmer" />
          </div>
          {[...Array(6)].map((_, i) => (
            <div key={i} className="flex items-center gap-3 px-3 py-2">
              <div className="w-4 h-4 rounded bg-surface-muted skeleton-shimmer" />
              <div className="flex-1 h-2 rounded bg-surface-muted skeleton-shimmer" />
            </div>
          ))}
          <div className="pt-4 border-t border-border-color space-y-3">
            <div className="flex items-center gap-3 px-3 py-2">
              <div className="w-4 h-4 rounded bg-surface-muted skeleton-shimmer" />
              <div className="flex-1 h-2 rounded bg-surface-muted skeleton-shimmer" />
            </div>
            <div className="flex items-center gap-3 px-3 py-2">
              <div className="w-4 h-4 rounded bg-surface-muted skeleton-shimmer" />
              <div className="flex-1 h-2 rounded bg-surface-muted skeleton-shimmer" />
            </div>
          </div>
        </div>

        {/* Main content skeleton */}
        <div className="flex-1 p-6 lg:p-8 space-y-6 overflow-y-auto">
          {/* Progress bar */}
          <div className="w-full h-2 bg-border-color rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-600 rounded-full skeleton-shimmer"
              style={{ width: "60%" }}
            />
          </div>

          {/* Header banner skeleton */}
          <div className="bg-surface rounded-2xl border border-border-color shadow-sm p-6 space-y-3">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <div className="w-32 h-2 rounded bg-border-color skeleton-shimmer" />
                <div className="w-48 h-5 rounded bg-border-color skeleton-shimmer" />
                <div className="w-64 h-3 rounded bg-surface-muted skeleton-shimmer" />
              </div>
              <div className="w-24 h-8 rounded-xl bg-border-color skeleton-shimmer" />
            </div>
          </div>

          {/* Cards skeleton */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-surface rounded-2xl border border-border-color shadow-sm p-6 space-y-4">
                <div className="w-32 h-4 rounded bg-border-color skeleton-shimmer" />
                <div className="space-y-3">
                  {[...Array(3)].map((_, j) => (
                    <div key={j} className="w-full h-10 rounded-xl bg-surface-muted skeleton-shimmer" />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <span className="sr-only">Loading content, please wait...</span>
    </div>
  );
}
