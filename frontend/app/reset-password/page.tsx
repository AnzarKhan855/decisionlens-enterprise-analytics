"use client";

import React, { useState, Suspense, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import api from "@/lib/api";
import { Lock, Eye, EyeOff, ShieldCheck, CheckCircle2, ArrowRight } from "lucide-react";

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const redirectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    return () => {
      if (redirectTimerRef.current) clearTimeout(redirectTimerRef.current);
    };
  }, []);

  const isLengthOk = newPassword.length >= 6;
  const isMatch = newPassword && newPassword === confirmPassword;

  async function handleResetSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isLengthOk) {
      setError("Password must be at least 6 characters long.");
      return;
    }
    if (!isMatch) {
      setError("Passwords do not match.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      await api.post("/auth/reset-password", {
        reset_token: token,
        new_password: newPassword
      });

      setSuccess(true);
      redirectTimerRef.current = setTimeout(() => {
        window.location.href = "/login";
      }, 1500);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Invalid or expired password reset link.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-md premium-card p-6 lg:p-8 space-y-6 relative z-10">
      <div className="text-center space-y-2">
        <div className="w-12 h-12 rounded-2xl bg-primary-600 text-white font-bold text-lg flex items-center justify-center mx-auto shadow-lg shadow-primary-600/30" aria-label="DecisionLens logo">
          DL
        </div>
        <h1 className="text-2xl font-bold text-text-primary tracking-tight">Set New Password</h1>
        <p className="text-xs text-text-muted">Choose a new secure password for your account</p>
      </div>

      {!success ? (
        <form onSubmit={handleResetSubmit} className="space-y-4">
          <div>
            <label htmlFor="reset-password" className="block text-xs font-semibold text-text-secondary mb-1.5">New Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-text-muted absolute left-3.5 top-3" aria-hidden="true" />
              <input
                id="reset-password"
                type={showPassword ? "text" : "password"}
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-10 pr-10 py-2.5 bg-background/60 border border-border-color rounded-xl text-xs text-text-primary placeholder:text-text-muted outline-none focus:border-primary-500 transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-3 text-text-muted hover:text-text-primary"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div>
            <label htmlFor="reset-confirm" className="block text-xs font-semibold text-text-secondary mb-1.5">Confirm New Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-text-muted absolute left-3.5 top-3" aria-hidden="true" />
              <input
                id="reset-confirm"
                type={showPassword ? "text" : "password"}
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-10 pr-10 py-2.5 bg-background/60 border border-border-color rounded-xl text-xs text-text-primary placeholder:text-text-muted outline-none focus:border-primary-500 transition-colors"
              />
            </div>
          </div>

          <div className="space-y-1 text-[11px] text-text-muted pt-1">
            <div className={`flex items-center gap-1.5 ${isLengthOk ? "text-success-400" : "text-text-muted"}`}>
              <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
              <span>At least 6 characters</span>
            </div>
            <div className={`flex items-center gap-1.5 ${isMatch ? "text-success-400" : "text-text-muted"}`}>
              <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Passwords match</span>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-error-500/10 border border-error-500/30 rounded-xl text-error-400 text-xs text-center font-medium" role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !isLengthOk || !isMatch}
            className="w-full py-3 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white font-semibold text-xs rounded-xl transition-all shadow-lg shadow-primary-600/30 flex items-center justify-center gap-2"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" aria-hidden="true" />
            ) : (
              <>
                <span>Update Password</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      ) : (
        <div className="p-4 bg-success-500/10 border border-success-500/30 rounded-2xl space-y-3 text-center">
          <CheckCircle2 className="w-8 h-8 text-success-400 mx-auto" aria-hidden="true" />
          <h3 className="text-sm font-bold text-text-primary">Password Updated!</h3>
          <p className="text-xs text-text-secondary">
            Your password has been successfully reset. Redirecting to login portal...
          </p>
        </div>
      )}
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6 text-text-primary relative overflow-hidden">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-primary-600/20 rounded-full blur-3xl pointer-events-none" />
      <Suspense fallback={<div className="text-text-muted text-xs">Loading Security Token...</div>}>
        <ResetPasswordContent />
      </Suspense>
    </div>
  );
}
