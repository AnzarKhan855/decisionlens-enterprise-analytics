"use client";

import React, { useEffect } from "react";
import { RefreshCw, AlertTriangle, Bug, Mail, ArrowLeft } from "lucide-react";
import Button from "@/components/ui/Button";

// QA NOTE: This is the global error boundary. It must remain free of placeholder text.
// If you see "TODO" or "fix me" here, it's a regression. Remove immediately.

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error("[Global Error Boundary]", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-surface-muted flex items-center justify-center p-6">
      <div className="max-w-lg w-full">
         <div className="premium-card rounded-2xl p-8 space-y-6 text-center">
          <div className="w-16 h-16 rounded-full bg-warning-50 border border-warning-100 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-8 h-8 text-warning-600" />
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-extrabold text-text-primary">Something went wrong</h1>
            <p className="text-sm text-text-muted leading-relaxed">
              An unexpected error occurred while rendering this page. Our team has been notified.
            </p>
          </div>

          <div className="bg-surface-muted rounded-xl p-4 text-left space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-text-muted uppercase tracking-wider">
              <Bug className="w-3.5 h-3.5" />
              Diagnostic Information
            </div>
            <div className="text-xs text-text-secondary font-mono bg-surface rounded-lg p-3 border border-border-light break-all">
              {error.digest || error.message || "Unknown error"}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Button onClick={reset} variant="primary" icon={<RefreshCw className="w-4 h-4" />}>
              Try Again
            </Button>
            <Button
              onClick={() => (window.location.href = "/")}
              variant="secondary"
              icon={<ArrowLeft className="w-4 h-4" />}
            >
              Go Home
            </Button>
          </div>

          <div className="flex items-center justify-center gap-2 text-xs text-text-muted">
            <Mail className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Still stuck? Contact support at support@decisionlens.ai</span>
          </div>
        </div>
      </div>
    </div>
  );
}
