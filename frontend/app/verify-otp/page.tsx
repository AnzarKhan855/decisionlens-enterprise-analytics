"use client";

import React, { useState, useEffect, Suspense, useRef } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import api from "@/lib/api";
import { KeyRound, ShieldCheck, ArrowLeft, RefreshCw, CheckCircle2 } from "lucide-react";

function VerifyOTPContent() {
  const searchParams = useSearchParams();
  const email = searchParams.get("email") || "";
  const devOtpParam = searchParams.get("dev_otp") || "";
  const redirectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [otpCode, setOtpCode] = useState(devOtpParam);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [countdown, setCountdown] = useState(60);

  useEffect(() => {
    return () => {
      if (redirectTimerRef.current) clearTimeout(redirectTimerRef.current);
    };
  }, []);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (countdown > 0) {
      timer = setInterval(() => setCountdown((prev) => prev - 1), 1000);
    }
    return () => clearInterval(timer);
  }, [countdown]);

  async function handleVerifySubmit(e: React.FormEvent) {
    e.preventDefault();
    if (otpCode.length < 6) return;

    try {
      setLoading(true);
      setError("");

      const res = await api.post("/auth/verify-otp", { email, otp_code: otpCode });
      if (res.data.access_token) {
        localStorage.setItem("decisionlens_access_token", res.data.access_token);
        if (res.data.refresh_token) {
          localStorage.setItem("decisionlens_refresh_token", res.data.refresh_token);
        }
        if (res.data.user) {
          localStorage.setItem("decisionlens_user", JSON.stringify(res.data.user));
        }
        setSuccess("Verification successful! Initializing secure session...");
        redirectTimerRef.current = setTimeout(() => {
          window.location.href = "/dynamic-dashboard";
        }, 800);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Invalid or expired verification code.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }

  async function handleResendOTP() {
    if (countdown > 0) return;
    try {
      setResending(true);
      setError("");
      setSuccess("");

      const res = await api.post("/auth/resend-otp", { email });
      setSuccess("New 6-digit verification code sent to your registered email!");
      setCountdown(60);
      if (res.data.dev_otp) {
        setOtpCode(res.data.dev_otp);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to resend verification code. Please try again later.";
      setError(errorMessage);
    } finally {
      setResending(false);
    }
  }

  return (
    <div className="w-full max-w-md premium-card p-6 lg:p-8 space-y-6 relative z-10">
      <div className="text-center space-y-2">
        <div className="w-12 h-12 rounded-2xl bg-primary-600 text-white font-bold text-lg flex items-center justify-center mx-auto shadow-lg shadow-primary-600/30" aria-label="DecisionLens logo">
          <KeyRound className="w-6 h-6" />
        </div>
        <h1 className="text-2xl font-bold text-text-primary tracking-tight">Enter Verification Code</h1>
        <p className="text-xs text-text-muted">
          A 6-digit security code was sent to <strong className="text-primary-300 font-mono">{email || "your registered email"}</strong>
        </p>
      </div>

      <form onSubmit={handleVerifySubmit} className="space-y-4">
        <div>
          <label htmlFor="otp-code" className="block text-xs font-semibold text-text-secondary mb-1.5 text-center">
            6-Digit Security Verification Code
          </label>
          <input
            id="otp-code"
            type="text"
            maxLength={6}
            required
            value={otpCode}
            onChange={(e) => setOtpCode(e.target.value)}
            placeholder="••••••"
            className="w-full py-3 bg-background/80 border border-border-color rounded-xl text-lg text-text-primary font-mono tracking-[0.5em] text-center outline-none focus:border-primary-500 transition-colors"
          />
          <span className="block text-[11px] text-text-muted text-center mt-1">Code expires in 5 minutes</span>
        </div>

        {success && (
          <div className="p-3 bg-success-500/10 border border-success-500/30 rounded-xl text-success-400 text-xs text-center font-medium flex items-center justify-center gap-2" role="status">
            <CheckCircle2 className="w-4 h-4" />
            <span>{success}</span>
          </div>
        )}

        {error && (
          <div className="p-3 bg-error-500/10 border border-error-500/30 rounded-xl text-error-400 text-xs text-center font-medium" role="alert">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || otpCode.length < 6}
          className="w-full py-3 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white font-semibold text-xs rounded-xl transition-all shadow-lg shadow-primary-600/30 flex items-center justify-center gap-2"
        >
          {loading ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" aria-hidden="true" />
          ) : (
            <>
              <ShieldCheck className="w-4 h-4" />
              <span>Verify & Complete Sign In</span>
            </>
          )}
        </button>
      </form>

      <div className="flex items-center justify-between text-xs pt-2">
        <button
          onClick={handleResendOTP}
          disabled={countdown > 0 || resending}
          className="text-primary-400 hover:underline disabled:opacity-50 disabled:no-underline flex items-center gap-1 font-semibold cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${resending ? "animate-spin" : ""}`} aria-hidden="true" />
          <span>{countdown > 0 ? `Resend Code in ${countdown}s` : "Resend Code"}</span>
        </button>

        <Link href="/login" className="text-text-muted hover:text-text-primary flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
          <span>Back to Login</span>
        </Link>
      </div>
    </div>
  );
}

export default function VerifyOTPPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6 text-text-primary relative overflow-hidden">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-primary-600/20 rounded-full blur-3xl pointer-events-none" />
      <Suspense fallback={<div className="text-text-muted text-xs">Loading Security Context...</div>}>
        <VerifyOTPContent />
      </Suspense>
    </div>
  );
}
