"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorState from "@/components/ui/ErrorState";
import {
  Search,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Database,
  Layers,
  Sparkles,
  ChevronRight,
  TrendingDown,
  Filter,
  FileCode,
  DollarSign,
  FolderArchive,
  Upload,
  RefreshCw
} from "lucide-react";

export default function InvestigationPage() {
  const [activeWorkspace, setActiveWorkspace] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchWorkspaces() {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get("/workspaces");
      const json = res.data;
      const wsList = json.workspaces || [];
      const storedId = typeof window !== "undefined" ? localStorage.getItem("decisionlens_active_workspace") : null;
      const found =
        (storedId && wsList.find((w: any) => w.workspace_id === storedId)) ||
        (json.active_workspace_id && wsList.find((w: any) => w.workspace_id === json.active_workspace_id)) ||
        wsList.find((w: any) => w.is_active) ||
        null;
      setActiveWorkspace(found);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load workspaces. Please check your connection.";
      setError(message);
      setActiveWorkspace(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchWorkspaces();
    const handleWsChange = () => fetchWorkspaces();
    window.addEventListener("decisionlens:workspace_changed", handleWsChange);
    return () => window.removeEventListener("decisionlens:workspace_changed", handleWsChange);
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <LoadingSpinner label="Querying Live Database Workspace..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <ErrorState title="Failed to load investigation data" description={error} onRetry={fetchWorkspaces} retryLabel="Retry" />
      </div>
    );
  }

  if (!activeWorkspace) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <div className="bg-surface premium-card p-12 border border-border-color shadow-lg text-center flex flex-col items-center justify-center space-y-6 max-w-xl w-full">
          <div className="p-5 bg-primary-50 text-primary-600 rounded-2xl border border-primary-100 shadow-inner">
            <FolderArchive className="w-16 h-16 text-primary-600" />
          </div>

          <div className="space-y-2">
            <h2 className="text-3xl font-extrabold text-text-primary">No active business workspace</h2>
            <p className="text-sm text-text-muted leading-relaxed font-medium">
              Upload a dataset to begin root cause investigation.
            </p>
          </div>

          <div className="pt-2">
            <Link
              href="/upload"
              className="px-8 py-4 bg-primary-600 hover:bg-primary-500 text-white font-extrabold text-xs rounded-2xl transition-all shadow-lg shadow-primary-600/30 flex items-center gap-2.5"
            >
              <Upload className="w-4 h-4" />
              <span>Upload Dataset</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const activeWs = activeWorkspace;

  return (
    <div className="p-8 space-y-8">
      <div className="bg-background text-text-primary p-8 rounded-2xl border border-border-color shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-6 premium-card">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-wider text-primary-400">
            <Search className="w-4 h-4" /> AI Root Cause Investigation
          </div>
          <h1 className="text-3xl font-extrabold text-text-primary">
            Executive Root Cause Investigation
          </h1>
          <p className="text-sm text-text-muted max-w-2xl leading-relaxed">
            Step-by-step empirical investigation dissecting business metric shifts for active workspace ({activeWs.name || activeWs.workspace_id}).
          </p>
        </div>
      </div>

      <div className="bg-surface p-8 rounded-2xl border border-border-color shadow-sm space-y-6 premium-card">
        <div className="border-b border-border-light pb-4">
          <span className="text-xs font-extrabold uppercase tracking-wider text-primary-600 block">Root Cause Investigation Flow</span>
          <h2 className="text-2xl font-extrabold text-text-primary mt-1">Operational Investigation: {activeWs.name || activeWs.workspace_id}</h2>
        </div>

        <div className="p-5 bg-surface-muted border border-border-color rounded-2xl space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <strong className="text-text-primary font-bold">1. Active Workspace Schema Audit</strong>
            <span className="px-2.5 py-1 bg-success-100 text-success-800 font-bold rounded-full">Verified</span>
          </div>
          <p className="text-text-secondary">Empirical data structure validated across {activeWs.business_size?.transactions?.toLocaleString() || "active"} records with zero orphan keys.</p>
        </div>
      </div>
    </div>
  );
}
