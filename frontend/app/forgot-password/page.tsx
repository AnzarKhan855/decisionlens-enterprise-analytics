"use client";

import React, { useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import { Mail, ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      setLoading(true);
      setError("");

      await api.post("/auth/forgot-password", { email });
      setSubmitted(true);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to process password reset request.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6 text-text-primary relative overflow-hidden">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-primary-600/20 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md premium-card p-6 lg:p-8 space-y-6 relative z-10">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-primary-600 text-white font-bold text-lg flex items-center justify-center mx-auto shadow-lg shadow-primary-600/30" aria-label="DecisionLens logo">
            DL
          </div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">Reset Password</h1>
          <p className="text-xs text-text-muted">
            Enter your work email to receive password reset instructions
          </p>
        </div>

        {!submitted ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="forgot-email" className="block text-xs font-semibold text-text-secondary mb-1.5">Work Email Address</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-text-muted absolute left-3.5 top-3" aria-hidden="true" />
                <input
                  id="forgot-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@decisionlens.ai"
                  className="w-full pl-10 pr-4 py-2.5 bg-background/60 border border-border-color rounded-xl text-xs text-text-primary placeholder:text-text-muted outline-none focus:border-primary-500 transition-colors font-mono"
                />
              </div>
            </div>

            {error && (
              <div className="p-3 bg-error-500/10 border border-error-500/30 rounded-xl text-error-400 text-xs text-center font-medium" role="alert">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-primary-600 hover:bg-primary-500 text-white font-semibold text-xs rounded-xl transition-all shadow-lg shadow-primary-600/30 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" aria-hidden="true" />
              ) : (
                <>
                  <span>Send Reset Link</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        ) : (
          <div className="p-4 bg-success-500/10 border border-success-500/30 rounded-2xl space-y-3 text-center">
            <CheckCircle2 className="w-8 h-8 text-success-400 mx-auto" aria-hidden="true" />
            <h3 className="text-sm font-bold text-text-primary">Reset Link Dispatched</h3>
            <p className="text-xs text-text-secondary">
              If an account exists for <strong className="text-primary-300 font-mono">{email}</strong>, a password reset link expiring in 15 minutes has been sent to your email.
            </p>
          </div>
        )}

        <div className="text-center pt-2">
          <Link href="/login" className="text-xs text-text-muted hover:text-text-primary inline-flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Back to Login</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
