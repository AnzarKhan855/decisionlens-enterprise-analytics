"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorState from "@/components/ui/ErrorState";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Activity,
  Zap,
  Server,
  RefreshCw,
  Search,
  ChevronDown,
  ChevronUp,
  FileCode,
  Globe,
  Terminal,
  Lock,
  Cpu,
  CheckCircle2,
  FolderArchive,
  Upload
} from "lucide-react";

export default function CybersecurityIntelligencePage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCybersecurityData();
  }, []);

  async function fetchCybersecurityData() {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get("/cybersecurity/dashboard");
      setData(res.data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load cybersecurity data. Please check your connection.";
      setError(message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <LoadingSpinner label="Querying Live Cybersecurity SOC Intelligence..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <ErrorState title="Failed to load cybersecurity intelligence" description={error} onRetry={fetchCybersecurityData} retryLabel="Retry" />
      </div>
    );
  }

  if (!data) {
    return (
    <div className="p-8 flex items-center justify-center min-h-[70vh]">
      <div className="bg-surface premium-card p-12 border border-border-color shadow-lg text-center flex flex-col items-center justify-center space-y-6 max-w-xl w-full">
        <div className="p-5 bg-error-50 text-error-600 rounded-2xl border border-error-100 shadow-inner">
            <ShieldAlert className="w-16 h-16 text-error-600" />
          </div>

          <div className="space-y-2">
            <h2 className="text-3xl font-extrabold text-text-primary">No Active Business Workspace</h2>
            <p className="text-sm text-text-muted leading-relaxed font-medium">
              Upload a firewall, SIEM, or security log dataset (.csv, .parquet, .json) to begin AI SOC threat intelligence analysis.
            </p>
          </div>

          <div className="pt-2">
            <Link
              href="/upload"
              className="px-8 py-4 bg-primary-600 hover:bg-primary-500 text-white font-extrabold text-xs rounded-2xl transition-all shadow-lg shadow-primary-600/30 flex items-center gap-2.5"
            >
              <Upload className="w-4 h-4" />
              <span>Upload Security Dataset</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
          <div className="bg-gradient-to-r from-error-600 via-error-50 to-primary-600 dark:from-error-800 dark:via-background dark:to-primary-800 p-8 rounded-2xl border border-error-800/40 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-6 premium-card">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 bg-error-500/20 text-error-400 font-extrabold text-xs rounded-full border border-error-500/30 uppercase tracking-wide flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5" /> SOC Threat Intelligence
                </span>
                <span className="px-3 py-1 bg-primary-500/20 text-primary-300 font-extrabold text-xs rounded-full border border-primary-500/30">
                  Domain: {data.domain || "Cybersecurity"}
                </span>
              </div>

              <h1 className="text-3xl font-extrabold text-text-primary flex items-center gap-3">
                <span>Security Operations Center (SOC) Console</span>
              </h1>
              <p className="text-sm text-text-muted max-w-2xl leading-relaxed">
                Zero-trust threat vector assessment across {data.analyzed_log_events?.toLocaleString() || 0} empirical security log events.
              </p>
            </div>

            <div className="p-4 bg-background/80 rounded-2xl border border-error-500/30 text-center space-y-1">
              <span className="text-[10px] uppercase tracking-wider text-text-muted font-bold block">SOC Risk Posture</span>
              <strong className="text-2xl font-extrabold text-error-400 block">{data.overall_soc_risk_score || 0} / 100</strong>
            </div>
          </div>
    </div>
  );
}
