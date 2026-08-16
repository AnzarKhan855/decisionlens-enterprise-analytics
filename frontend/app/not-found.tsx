"use client";

import React from "react";
import Link from "next/link";
import { Home, Search, ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-surface-muted flex items-center justify-center p-6">
      <div className="max-w-lg w-full">
         <div className="premium-card rounded-2xl overflow-hidden">
          <div className="p-8 pb-6 text-center">
            <div className="w-20 h-20 rounded-full bg-primary-50 border border-primary-100 flex items-center justify-center mx-auto mb-6">
              <span className="text-3xl font-extrabold text-primary-600">404</span>
            </div>

            <h1 className="text-2xl font-extrabold text-text-primary mb-2">Page Not Found</h1>
            <p className="text-sm text-text-muted leading-relaxed max-w-sm mx-auto">
              The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.
            </p>
          </div>

          <div className="px-8 pb-8 space-y-3">
            <div className="bg-surface-muted rounded-xl p-4 text-xs text-text-muted text-center">
              <Search className="w-4 h-4 text-text-muted mx-auto mb-2" aria-hidden="true" />
              Check the URL for typos or use the navigation to find what you need.
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <Link href="/" className="inline-flex items-center gap-2 px-6 py-3.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-extrabold rounded-2xl transition-all shadow-lg shadow-primary-600/30">
                <Home className="w-4 h-4" />
                Back to Dashboard
              </Link>
              <button
                onClick={() => window.history.back()}
                aria-label="Go back to previous page"
                className="inline-flex items-center gap-2 px-6 py-3.5 bg-surface hover:bg-surface-muted text-text-secondary text-xs font-extrabold rounded-2xl transition-all border border-border-color shadow-sm"
              >
                <ArrowLeft className="w-4 h-4" />
                Go Back
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
