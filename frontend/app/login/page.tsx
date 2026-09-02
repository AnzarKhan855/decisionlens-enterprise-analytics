"use client";

import React, { useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import { ArrowRight, Lock, Mail, Eye, EyeOff, ShieldCheck, UserCheck } from "lucide-react";

export default function LoginPage() {
  const [selectedRole, setSelectedRole] = useState<"SUPER_ADMIN" | "ORGANIZATION_ADMIN" | "EMPLOYEE">("SUPER_ADMIN");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLoginSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      setLoading(true);
      setError("");

      const res = await api.post("/auth/login", { email, password, role: selectedRole });
      if (res.data.otp_required) {
        const searchParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
        const redirectParam = searchParams?.get("redirect");
        const redirectSuffix = redirectParam ? `&redirect=${encodeURIComponent(redirectParam)}` : "";
        const devOtp = res.data.dev_otp ? `&dev_otp=${encodeURIComponent(res.data.dev_otp)}` : "";
        window.location.href = `/verify-otp?email=${encodeURIComponent(email)}${devOtp}${redirectSuffix}`;
      } else if (res.data.access_token) {
        const token = res.data.access_token;
        localStorage.setItem("decisionlens_access_token", token);
        if (res.data.refresh_token) {
          localStorage.setItem("decisionlens_refresh_token", res.data.refresh_token);
        }
        if (res.data.user) {
          localStorage.setItem("decisionlens_user", JSON.stringify(res.data.user));
        }

        // Set session cookie for Next.js Edge Middleware route protection
        const isSecure = typeof window !== "undefined" && window.location.protocol === "https:" ? "; Secure" : "";
        document.cookie = `decisionlens_token=${encodeURIComponent(token)}; Path=/; Max-Age=86400; SameSite=Lax${isSecure};`;

        // Preserve and redirect to target deep link if requested
        const searchParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
        const redirectParam = searchParams?.get("redirect");
        const destination = redirectParam && redirectParam.startsWith("/") ? redirectParam : "/dynamic-dashboard";
        window.location.href = destination;
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Invalid credentials. Please verify email and password.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6 text-text-primary relative overflow-hidden">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-primary-600/20 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-surface backdrop-blur-md border border-border-color p-8 rounded-2xl shadow-lg space-y-6 relative z-10">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-primary-600 text-white font-bold text-lg flex items-center justify-center mx-auto shadow-lg shadow-primary-600/30" aria-label="DecisionLens logo">
            DL
          </div>
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">DecisionLens Enterprise</h1>
          <p className="text-xs text-text-muted">Sign in to your Enterprise Account</p>
        </div>

        <form onSubmit={handleLoginSubmit} className="space-y-4">
          <fieldset>
            <legend className="block text-xs font-semibold text-text-secondary mb-1.5 flex items-center gap-1.5">
              <UserCheck className="w-3.5 h-3.5 text-primary-400" aria-hidden="true" />
              <span>Login as:</span>
            </legend>
            <div className="grid grid-cols-3 gap-2">
              {(["SUPER_ADMIN", "ORGANIZATION_ADMIN", "EMPLOYEE"] as const).map((role) => (
                <button
                  key={role}
                  type="button"
                  onClick={() => setSelectedRole(role)}
                  className={`
                    py-2 px-2 text-[11px] font-medium rounded-xl border text-center transition-all cursor-pointer
                    ${selectedRole === role
                      ? "bg-primary-600 text-white shadow-sm"
                      : "bg-background/40 border-border-color text-text-muted hover:text-text-secondary"
                    }
                  `}
                  aria-pressed={selectedRole === role}
                >
                  {role === "SUPER_ADMIN" ? "Super Admin" : role === "ORGANIZATION_ADMIN" ? "Org Admin" : "Employee"}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-text-muted mt-1.5 text-center">
              {selectedRole === "SUPER_ADMIN" ? "Requires Password + OTP Verification" : "Requires Password Only (Direct Sign-In)"}
            </p>
          </fieldset>

          <div>
            <label htmlFor="login-email" className="block text-xs font-semibold text-text-secondary mb-1.5">Work Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-text-muted absolute left-3.5 top-3" aria-hidden="true" />
              <input
                id="login-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@enterprise.com"
                  className="w-full pl-10 pr-4 py-2.5 bg-background/60 border border-border-color rounded-xl text-xs text-text-primary placeholder:text-text-muted outline-none focus:border-primary-500 transition-colors font-mono"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label htmlFor="login-password" className="block text-xs font-semibold text-text-secondary">Password</label>
              <Link href="/forgot-password" className="text-[11px] text-primary-400 hover:underline">Forgot password?</Link>
            </div>
            <div className="relative">
              <Lock className="w-4 h-4 text-text-muted absolute left-3.5 top-3" aria-hidden="true" />
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
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
                <ShieldCheck className="w-4 h-4" aria-hidden="true" />
                <span>{selectedRole === "SUPER_ADMIN" ? "Sign In & Request OTP" : "Sign In Directly"}</span>
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </>
            )}
          </button>
        </form>

        <div className="text-center pt-4 border-t border-border-color text-xs text-text-muted">
          Don&apos;t have an enterprise account?{" "}
          <Link href="/register" className="text-primary-400 font-semibold hover:underline">
            Request Workspace Access
          </Link>
        </div>
      </div>
    </div>
  );
}
