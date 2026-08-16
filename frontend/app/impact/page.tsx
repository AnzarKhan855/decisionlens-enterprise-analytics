"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorState from "@/components/ui/ErrorState";
import {
  DollarSign,
  TrendingUp,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Target,
  ArrowRight,
  ShieldCheck,
  Award,
  Sparkles,
  Clock,
  User,
  Layers,
  FolderArchive,
  Upload,
  RefreshCw
} from "lucide-react";

export default function BusinessImpactPage() {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  async function fetchWorkspaces() {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get("/workspaces");
      const json = res.data;
      setWorkspaces(json.workspaces || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load business impact data. Please check your connection.";
      setError(message);
      setWorkspaces([]);
    } finally {
      setLoading(false);
    }
  }

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
        <ErrorState title="Failed to load business impact data" description={error} onRetry={fetchWorkspaces} retryLabel="Retry" />
      </div>
    );
  }

  if (workspaces.length === 0) {
    return (
    <div className="p-8 flex items-center justify-center min-h-[70vh]">
      <div className="bg-surface premium-card p-12 border border-border-color shadow-lg text-center flex flex-col items-center justify-center space-y-6 max-w-xl w-full">
        <div className="p-5 bg-primary-50 text-primary-600 rounded-2xl border border-primary-100 shadow-inner">
            <FolderArchive className="w-16 h-16 text-primary-600" />
          </div>

          <div className="space-y-2">
            <h2 className="text-3xl font-extrabold text-text-primary">No active business workspace</h2>
            <p className="text-sm text-text-muted leading-relaxed font-medium">
              Upload a dataset to evaluate business financial impact.
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

  const activeWs = workspaces[0];

  return (
    <div className="p-8 space-y-8">
          <div className="bg-gradient-to-r from-surface via-primary-50 to-surface dark:from-background dark:via-primary-800 dark:to-background text-text-primary dark:text-white p-8 rounded-2xl border border-border-color shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-6 premium-card">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 bg-success-500/20 text-success-300 text-xs font-extrabold rounded-full border border-success-500/30 uppercase tracking-wide flex items-center gap-1">
                  <DollarSign className="w-3.5 h-3.5 text-success-400" /> Financial Impact Analysis
                </span>
              </div>

              <h1 className="text-3xl font-extrabold text-text-primary">
                Where Should I Focus First?
              </h1>
              <p className="text-sm text-text-muted max-w-2xl leading-relaxed">
                Prioritized executive focus matrix generated for active workspace ({activeWs.name}).
              </p>
            </div>

            <div className="flex items-center gap-3 self-start md:self-auto">
              <Link
                href="/decisions"
                className="px-6 py-3.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-extrabold rounded-2xl transition-all shadow-lg shadow-primary-600/30 flex items-center gap-2"
              >
                <Zap className="w-4 h-4" />
                <span>Open Decision Center</span>
              </Link>
            </div>
          </div>
    </div>
  );
}
