"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { ArrowRight, Lock, Mail, User, Building, ShieldCheck, CheckCircle2 } from "lucide-react";
import { apiPost } from "@/lib/api";

const STEPS = [
  { id: 1, label: "Personal Info" },
  { id: 2, label: "Organization" },
  { id: 3, label: "Security" },
] as const;

export default function RegisterPage() {
  const [step, setStep] = useState(1);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [organization, setOrganization] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  const redirectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (redirectTimerRef.current) clearTimeout(redirectTimerRef.current);
    };
  }, []);

  const passwordChecks = {
    length: password.length >= 8,
    hasUpper: /[A-Z]/.test(password),
    hasLower: /[a-z]/.test(password),
    hasNumber: /[0-9]/.test(password),
  };

  const allPasswordChecks = Object.values(passwordChecks).every(Boolean);
  const canProceedStep1 = fullName.trim().length > 0 && email.trim().length > 0 && email.includes("@");
  const canProceedStep2 = organization.trim().length > 0;
  const canSubmit = allPasswordChecks && canProceedStep1 && canProceedStep2;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      setLoading(true);
      const data = await apiPost<{ message?: string; detail?: string }>("/auth/register", {
        email,
        password,
        full_name: fullName,
        organization,
        role: "EMPLOYEE",
      });
      if (data.detail) {
        setError(data.detail);
      } else {
        setSuccess(true);
        redirectTimerRef.current = setTimeout(() => {
          window.location.href = "/login";
        }, 2000);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Registration failed. Please check your credentials.";
      setError(msg);
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
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">Create Account</h1>
          <p className="text-xs text-text-muted">Join your organization on DecisionLens</p>
        </div>

        <div className="flex items-center justify-between px-2">
          {STEPS.map((s) => (
            <React.Fragment key={s.id}>
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-xs font-extrabold transition-all
                    ${step >= s.id ? "bg-primary-600 text-white shadow-md shadow-primary-600/30" : "bg-surface-muted text-text-muted"}
                  `}
                >
                  {step > s.id ? <CheckCircle2 className="w-4 h-4" /> : s.id}
                </div>
                <span className={`text-[10px] font-semibold ${step >= s.id ? "text-primary-300" : "text-text-muted"}`}>
                  {s.label}
                </span>
              </div>
              {s.id < STEPS.length && (
                <div className={`flex-1 h-0.5 mx-2 rounded-full ${step > s.id ? "bg-primary-600" : "bg-surface-muted"}`} />
              )}
            </React.Fragment>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label htmlFor="reg-name" className="block text-xs font-semibold text-text-secondary mb-1.5">Full Name</label>
                <div className="relative">
                  <User className="w-4 h-4 text-text-muted absolute left-3.5 top-3" aria-hidden="true" />
                  <input
                    id="reg-name"
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Anzar Khan"
                    className="w-full pl-10 pr-4 py-2.5 bg-background/60 border border-border-color rounded-xl text-xs text-text-primary placeholder:text-text-muted outline-none focus:border-primary-500 transition-colors"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="reg-email" className="block text-xs font-semibold text-text-secondary mb-1.5">Work Email</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-text-muted absolute left-3.5 top-3" aria-hidden="true" />
                  <input
                    id="reg-email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="anzar@enterprise.com"
                    className="w-full pl-10 pr-4 py-2.5 bg-background/60 border border-border-color rounded-xl text-xs text-text-primary placeholder:text-text-muted outline-none focus:border-primary-500 transition-colors"
                  />
                </div>
              </div>
              <button
                type="button"
                onClick={() => setStep(2)}
                disabled={!canProceedStep1}
                className="w-full py-3 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white font-semibold text-xs rounded-xl transition-all shadow-lg shadow-primary-600/30 flex items-center justify-center gap-2"
              >
                Continue
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div>
                <label htmlFor="reg-org" className="block text-xs font-semibold text-text-secondary mb-1.5">Organization</label>
                <div className="relative">
                  <Building className="w-4 h-4 text-text-muted absolute left-3.5 top-3" aria-hidden="true" />
                  <input
                    id="reg-org"
                    type="text"
                    required
                    value={organization}
                    onChange={(e) => setOrganization(e.target.value)}
                    placeholder="Acme Global Corporation"
                    className="w-full pl-10 pr-4 py-2.5 bg-background/60 border border-border-color rounded-xl text-xs text-text-primary placeholder:text-text-muted outline-none focus:border-primary-500 transition-colors"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="flex-1 py-3 bg-surface-muted hover:bg-text-primary text-text-primary font-semibold text-xs rounded-xl transition-all"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={() => setStep(3)}
                  disabled={!canProceedStep2}
                  className="flex-1 py-3 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white font-semibold text-xs rounded-xl transition-all shadow-lg shadow-primary-600/30 flex items-center justify-center gap-2"
                >
                  Continue
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div>
                <label htmlFor="reg-password" className="block text-xs font-semibold text-text-secondary mb-1.5">Password</label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-text-muted absolute left-3.5 top-3" aria-hidden="true" />
                  <input
                    id="reg-password"
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    className="w-full pl-10 pr-4 py-2.5 bg-background/60 border border-border-color rounded-xl text-xs text-text-primary placeholder:text-text-muted outline-none focus:border-primary-500 transition-colors"
                  />
                </div>
                <div className="mt-2 space-y-1.5">
                  {[
                    { label: "At least 8 characters", check: passwordChecks.length },
                    { label: "One uppercase letter", check: passwordChecks.hasUpper },
                    { label: "One lowercase letter", check: passwordChecks.hasLower },
                    { label: "One number", check: passwordChecks.hasNumber },
                  ].map((item) => (
                    <div key={item.label} className={`flex items-center gap-1.5 text-[11px] ${item.check ? "text-success-400" : "text-text-muted"}`}>
                      <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
                      <span>{item.label}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="flex-1 py-3 bg-surface-muted hover:bg-text-primary text-text-primary font-semibold text-xs rounded-xl transition-all"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={loading || !canSubmit}
                  className="flex-1 py-3 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white font-semibold text-xs rounded-xl transition-all shadow-lg shadow-primary-600/30 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" aria-hidden="true" />
                  ) : (
                    <>
                      <span>Create Account</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 bg-error-500/10 border border-error-500/30 rounded-xl text-error-400 text-xs text-center font-medium" role="alert">
              {error}
            </div>
          )}

          {success && (
            <div className="p-3 bg-success-500/10 border border-success-500/30 rounded-xl text-success-400 text-xs text-center font-medium">
              Account created! Redirecting to login...
            </div>
          )}
        </form>

        <div className="text-center pt-4 border-t border-border-color text-xs text-text-muted">
          Already have an account?{" "}
          <Link href="/login" className="text-primary-400 font-semibold hover:underline">
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
