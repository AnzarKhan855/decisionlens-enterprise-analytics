"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import {
  Building2,
  CheckCircle2,
  TrendingUp,
  Users,
  ShoppingBag,
  Upload,
  RefreshCw,
  AlertCircle,
  ShieldCheck,
  FileText,
  FolderArchive,
  Zap,
  UserCheck,
  Mail,
  Shield,
  Key,
  LogOut,
  Sparkles,
} from "lucide-react";
import { useToast } from "@/lib/toast";

interface UserAccount {
  full_name: string;
  email: string;
  role: string;
  organization?: string;
  user_id?: string;
  created_at?: string;
}

interface ProfileData {
  workspace_name: string;
  industry: string;
  business_type: string;
  business_model: string;
  products_sold: string;
  countries: string;
  customers: string;
  sales_channels: string;
  revenue_model: string;
  main_kpis_available: string[];
  capabilities: {
    forecast_ready: boolean;
    customer_analytics_ready: boolean;
    inventory_analytics_ready: boolean;
    rag_ai_ready: boolean;
  };
  executive_questions_answerable: string[];
  business_health_score: number;
}

const CAPABILITY_ICONS: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  forecast_ready: { icon: <TrendingUp className="w-5 h-5" />, label: "Forecasting", color: "indigo" },
  customer_analytics_ready: { icon: <Users className="w-5 h-5" />, label: "Customer Analytics", color: "emerald" },
  inventory_analytics_ready: { icon: <ShoppingBag className="w-5 h-5" />, label: "Inventory Analytics", color: "amber" },
  rag_ai_ready: { icon: <Zap className="w-5 h-5" />, label: "AI Analysis", color: "violet" },
};

export default function BusinessProfilePage() {
  const [user, setUser] = useState<UserAccount | null>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { addToast } = useToast();

  async function loadAllData() {
    try {
      setLoading(true);
      setError(null);

      // Load user account
      const stored = typeof window !== "undefined" ? localStorage.getItem("decisionlens_user") : null;
      if (stored) {
        try { setUser(JSON.parse(stored)); } catch (e) { console.warn(e); }
      }
      const meRes = await api.get("/auth/me").catch(() => null);
      if (meRes?.data) {
        setUser(meRes.data);
        if (typeof window !== "undefined") {
          localStorage.setItem("decisionlens_user", JSON.stringify(meRes.data));
        }
      }

      // Load active workspace profile
      const wsRes = await api.get("/workspaces").catch(() => ({ data: { workspaces: [] } }));
      const list = wsRes.data?.workspaces || [];
      const storedId = typeof window !== "undefined" ? localStorage.getItem("decisionlens_active_workspace") : null;
      const activeWs =
        (storedId && list.find((w: any) => w.workspace_id === storedId)) ||
        (wsRes.data?.active_workspace_id && list.find((w: any) => w.workspace_id === wsRes.data?.active_workspace_id)) ||
        list.find((w: any) => w.is_active) ||
        (list.length > 0 ? list[0] : null);

      if (activeWs) {
        const res = await api.get(`/workspaces/${activeWs.workspace_id}/business-profile`).catch(() => ({ data: null }));
        if (res?.data) {
          setProfile(res.data);
        } else {
          setProfile(null);
        }
      } else {
        setProfile(null);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load user profile. Please check server connection.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAllData();
    const handleWsChange = () => loadAllData();
    window.addEventListener("decisionlens:workspace_changed", handleWsChange);
    return () => window.removeEventListener("decisionlens:workspace_changed", handleWsChange);
  }, []);

  function handleLogout() {
    localStorage.removeItem("decisionlens_access_token");
    localStorage.removeItem("decisionlens_user");
    localStorage.removeItem("decisionlens_active_workspace");
    if (typeof document !== "undefined") {
      document.cookie = "decisionlens_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";
    }
    addToast({ type: "info", title: "Signed out", description: "You have been logged out successfully." });
    window.location.href = "/login";
  }

  const fullName = user?.full_name || "Enterprise User";
  const userEmail = user?.email || "user@decisionlens.ai";
  const userRole = user?.role || "User";
  const organization = user?.organization || "DecisionLens Enterprise";
  const initials = fullName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2) || "EU";

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[70vh]" role="status" aria-label="Loading profile">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm font-semibold text-text-muted">Loading user & workspace profile...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 space-y-8 max-w-7xl mx-auto" aria-label="User & Business Profile">
      {/* Header Banner */}
      <div className="premium-card p-5 lg:p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-5">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 text-white font-extrabold text-2xl flex items-center justify-center shadow-lg shadow-primary-600/40 shrink-0 border border-border-color">
            {initials}
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-3 py-1 bg-primary-500/20 text-primary-300 text-xs font-extrabold rounded-full border border-primary-500/30 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" />
                {userRole.replace("_", " ").toUpperCase()}
              </span>
              <span className="px-3 py-1 bg-success-500/20 text-success-300 text-xs font-bold rounded-full border border-success-500/30">
                Verified Account
              </span>
            </div>
            <h1 className="text-3xl font-extrabold text-text-primary tracking-tight">{fullName}</h1>
            <p className="text-sm text-text-muted flex items-center gap-2">
              <Mail className="w-4 h-4 text-primary-400" />
              <span>{userEmail}</span>
              <span className="text-text-muted">•</span>
              <Building2 className="w-4 h-4 text-text-muted" />
              <span>{organization}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadAllData}
            className="px-4 py-3 bg-surface/10 hover:bg-surface/20 text-text-primary text-xs font-bold rounded-2xl transition-all border border-border-color/60 flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleLogout}
            className="px-5 py-3 bg-error-600 hover:bg-error-500 text-white text-xs font-extrabold rounded-2xl transition-all shadow-lg shadow-error-600/30 flex items-center gap-2"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Account Details & Workspace Overview Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Personal Details */}
        <div className="premium-card p-5 lg:p-6 space-y-4">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-600">
            <UserCheck className="w-4 h-4" /> Account Details
          </div>
          <div className="space-y-3 pt-2">
            <div>
              <span className="text-[10px] font-bold uppercase text-text-muted block">Full Name</span>
              <span className="text-sm font-extrabold text-text-primary">{fullName}</span>
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase text-text-muted block">Email Address</span>
              <span className="text-sm font-semibold text-text-primary font-mono">{userEmail}</span>
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase text-text-muted block">Assigned Role</span>
              <span className="inline-block px-2.5 py-1 text-xs font-bold bg-primary-50 text-primary-700 rounded-lg border border-primary-100 mt-0.5">
                {userRole.replace("_", " ")}
              </span>
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase text-text-muted block">Organization</span>
              <span className="text-xs font-semibold text-text-primary">{organization}</span>
            </div>
          </div>
        </div>

        {/* Security & Permissions */}
        <div className="premium-card p-5 lg:p-6 space-y-4">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-600">
            <Shield className="w-4 h-4" /> Security & Status
          </div>
          <div className="space-y-3 pt-2">
            <div className="p-3 bg-surface-muted border border-border-color rounded-2xl flex items-center justify-between">
              <span className="text-xs font-bold text-text-primary">Authentication</span>
              <span className="text-xs font-extrabold text-success-600 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> OAuth / JWT Active
              </span>
            </div>
            <div className="p-3 bg-surface-muted border border-border-color rounded-2xl flex items-center justify-between">
              <span className="text-xs font-bold text-text-primary">RBAC Clearance</span>
              <span className="text-xs font-extrabold text-primary-600">Full Workspace Access</span>
            </div>
            <div className="p-3 bg-surface-muted border border-border-color rounded-2xl flex items-center justify-between">
              <span className="text-xs font-bold text-text-primary">Data Isolation</span>
              <span className="text-xs font-extrabold text-success-600">Strict Single-Tenant</span>
            </div>
          </div>
        </div>

        {/* Active Workspace Card */}
        <div className="premium-card p-5 lg:p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-600">
              <Building2 className="w-4 h-4" /> Active Workspace
            </div>
            <Link href="/datasets" className="text-xs font-bold text-primary-600 hover:underline">
              Switch
            </Link>
          </div>
          {profile ? (
            <div className="space-y-3 pt-2">
              <div>
                <span className="text-[10px] font-bold uppercase text-text-muted block">Workspace Name</span>
                <span className="text-base font-extrabold text-text-primary">{profile.workspace_name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 bg-primary-50 text-primary-600 border border-primary-100 text-[11px] font-bold rounded-lg uppercase">
                  {profile.industry}
                </span>
                <span className="px-2.5 py-0.5 bg-success-50 text-success-600 border border-success-100 text-[11px] font-bold rounded-lg">
                  Score: {profile.business_health_score}/100
                </span>
              </div>
              <div className="pt-2">
                <Link
                  href="/dynamic-dashboard"
                  className="w-full py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-bold rounded-xl transition-all shadow-md text-center block"
                >
                  View Dynamic Dashboard
                </Link>
              </div>
            </div>
          ) : (
            <div className="text-center py-4 space-y-3">
              <p className="text-xs text-text-muted">No active dataset profile loaded.</p>
                <Link href="/upload" className="inline-block px-4 py-2 bg-primary-600 text-white text-xs font-bold rounded-xl shadow-md">
                Upload Dataset
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
