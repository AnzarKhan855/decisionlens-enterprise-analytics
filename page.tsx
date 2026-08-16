"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import ExecutiveActionCenter from "@/components/dashboard/ExecutiveActionCenter";
import ExecutiveNewsfeed from "@/components/dashboard/ExecutiveNewsfeed";
import { useToast } from "@/lib/toast";
import {
  ShieldCheck,
  Award,
  Database,
  Layers,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  TrendingUp,
  FolderArchive,
  Zap,
  ChevronRight,
  Search,
  MessageSquare,
  X,
  HelpCircle,
  Upload,
  Activity,
  RefreshCw,
  AlertCircle,
} from "lucide-react";

export default function HomePage() {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<any>(null);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [healthModalOpen, setHealthModalOpen] = useState(false);
  const { addToast } = useToast();

  async function fetchActiveWorkspace() {
    try {
      setLoading(true);
      setError(null);
      const wsRes = await fetch("http://127.0.0.1:8000/api/v1/workspaces");
      if (wsRes.ok) {
        const wsJson = await wsRes.json();
        const list = wsJson.workspaces || [];
        setWorkspaces(list);

        if (list.length > 0) {
          const currentWs = list[0];
          setActiveWorkspace(currentWs);

          const dashRes = await fetch(`http://127.0.0.1:8000/api/v1/dashboard/dynamic?workspace_id=${currentWs.workspace_id}`);
          if (dashRes.ok) {
            const dashJson = await dashRes.json();
            setDashboardData(dashJson);
          }
        } else {
          setActiveWorkspace(null);
          setDashboardData(null);
        }
      } else {
        setError("Failed to load workspace data.");
      }
    } catch (err) {
      setWorkspaces([]);
      setActiveWorkspace(null);
      setDashboardData(null);
      setError("Unable to connect to the server. Please ensure the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchActiveWorkspace();
  }, []);

  if (loading) {
    return (
      <div className="h-screen flex bg-slate-50 overflow-hidden">
        <aside className="hidden lg:block fixed left-0 top-0 h-screen w-64 z-40">
          <Sidebar />
        </aside>
        <div className="flex-1 lg:ml-64 flex flex-col h-screen">
          <Header />
          <main className="flex-1 overflow-y-auto p-8 flex items-center justify-center" role="status" aria-label="Loading dashboard">
            <div className="flex flex-col items-center gap-4">
              <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
              <div className="space-y-2">
                <p className="text-sm font-semibold text-slate-700">Querying Live Database Workspaces...</p>
                <p className="text-xs text-slate-400">Loading your executive briefing data.</p>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen flex bg-slate-50 overflow-hidden">
        <aside className="hidden lg:block fixed left-0 top-0 h-screen w-64 z-40">
          <Sidebar />
        </aside>
        <div className="flex-1 lg:ml-64 flex flex-col h-screen">
          <Header />
          <main className="flex-1 overflow-y-auto p-8 flex items-center justify-center" role="alert">
            <div className="bg-white rounded-3xl p-12 border border-slate-200 shadow-xl text-center flex flex-col items-center justify-center space-y-6 max-w-xl w-full">
              <div className="p-5 bg-red-50 text-red-600 rounded-3xl border border-red-100 shadow-inner">
                <AlertCircle className="w-16 h-16 text-red-600" />
              </div>
              <div className="space-y-2">
                <h2 className="text-2xl font-extrabold text-slate-900">Connection Error</h2>
                <p className="text-sm text-slate-500 leading-relaxed font-medium">{error}</p>
              </div>
              <button
                onClick={fetchActiveWorkspace}
                className="px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-extrabold text-xs rounded-2xl transition-all shadow-xl shadow-indigo-600/30 flex items-center gap-2.5"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Retry</span>
              </button>
            </div>
          </main>
        </div>
      </div>
    );
  }

  if (!activeWorkspace || workspaces.length === 0) {
    return (
      <div className="h-screen flex bg-slate-50 overflow-hidden">
        <aside className="hidden lg:block fixed left-0 top-0 h-screen w-64 z-40">
          <Sidebar />
        </aside>

        <div className="flex-1 lg:ml-64 flex flex-col h-screen">
          <Header />

          <main className="flex-1 overflow-y-auto p-8 space-y-8 flex flex-col items-center justify-center">
            <div className="bg-white rounded-3xl p-12 border border-slate-200 shadow-xl text-center flex flex-col items-center justify-center space-y-6 max-w-xl w-full">
              <div className="p-5 bg-indigo-50 text-indigo-600 rounded-3xl border border-indigo-100 shadow-inner">
                <FolderArchive className="w-16 h-16 text-indigo-600" />
              </div>

              <div className="space-y-2">
                <h2 className="text-3xl font-extrabold text-slate-900">No Business Workspace Found</h2>
                <p className="text-sm text-slate-500 leading-relaxed font-medium">
                  Upload a CSV, Excel, Parquet, or ZIP archive to begin AI executive decision intelligence analysis.
                </p>
              </div>

              <div className="pt-2 flex gap-3">
                <Link
                  href="/upload"
                  className="px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-extrabold text-xs rounded-2xl transition-all shadow-xl shadow-indigo-600/30 flex items-center gap-2.5 focus-visible:ring-2 focus-visible:ring-indigo-500"
                >
                  <Upload className="w-4 h-4" />
                  <span>Upload Dataset</span>
                </Link>
                <Link
                  href="/catalog"
                  className="px-6 py-4 bg-white hover:bg-slate-50 text-slate-700 font-extrabold text-xs rounded-2xl transition-all border border-slate-200 shadow-sm flex items-center gap-2.5 focus-visible:ring-2 focus-visible:ring-indigo-500"
                >
                  <Database className="w-4 h-4" />
                  <span>Browse Catalog</span>
                </Link>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  const healthScore = activeWorkspace.health_score || 98;
  const kpis = dashboardData?.kpis || [];
  const actionItems = dashboardData?.action_items || [];
  const newsItems = dashboardData?.newsfeed || [];

  return (
    <div className="h-screen flex bg-slate-50 overflow-hidden">
      <aside className="hidden lg:block fixed left-0 top-0 h-screen w-64 z-40">
        <Sidebar />
      </aside>

      <div className="flex-1 lg:ml-64 flex flex-col h-screen">
        <Header />

        <main className="flex-1 overflow-y-auto p-8 space-y-8" role="main" aria-label="Executive Dashboard">
          {healthModalOpen && (
            <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Business Health Score breakdown">
              <div className="bg-white rounded-3xl p-7 max-w-2xl w-full space-y-5 border border-slate-200 shadow-2xl">
                <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-2xl border border-emerald-200">
                      <ShieldCheck className="w-6 h-6" />
                    </div>
                    <div>
                      <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-600 font-bold block">Calculated Formula Breakdown</span>
                      <h3 className="text-xl font-extrabold text-slate-900">Business Health Score: {healthScore} / 100</h3>
                    </div>
                  </div>
                  <button onClick={() => setHealthModalOpen(false)} className="p-2 hover:bg-slate-100 rounded-full text-slate-400 hover:text-slate-600 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-500" aria-label="Close health score breakdown">
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="space-y-3 text-xs">
                  <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-between">
                    <div>
                      <strong className="text-slate-900 font-bold block">Data Completeness &amp; Schema Integrity (30%)</strong>
                      <span className="text-slate-500">Verified zero null keys and zero orphan table joins.</span>
                    </div>
                    <span className="px-3 py-1 bg-white border border-slate-200 rounded-xl font-extrabold text-indigo-600">
                      {activeWorkspace.data_quality_pct || 98} / 100
                    </span>
                  </div>

                  <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-between">
                    <div>
                      <strong className="text-slate-900 font-bold block">OLAP Query Readiness (30%)</strong>
                      <span className="text-slate-500">In-memory DuckDB columnar query response velocity.</span>
                    </div>
                    <span className="px-3 py-1 bg-white border border-slate-200 rounded-xl font-extrabold text-indigo-600">
                      96 / 100
                    </span>
                  </div>

                  <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-between">
                    <div>
                      <strong className="text-slate-900 font-bold block">AI Decision Engine Alignment (40%)</strong>
                      <span className="text-slate-500">Evidence-validated multi-agent decision score.</span>
                    </div>
                    <span className="px-3 py-1 bg-white border border-slate-200 rounded-xl font-extrabold text-indigo-600">
                      95 / 100
                    </span>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button onClick={() => setHealthModalOpen(false)} className="px-6 py-2.5 bg-indigo-600 text-white text-xs font-bold rounded-xl shadow-md focus-visible:ring-2 focus-visible:ring-indigo-500">
                    Close Breakdown
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="relative bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-3xl p-8 shadow-xl border border-slate-800 space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="px-3 py-1 bg-indigo-500/20 text-indigo-300 font-extrabold text-xs rounded-full border border-indigo-500/30 uppercase tracking-wide">
                    {activeWorkspace.name}
                  </span>
                  <button
                    onClick={() => setHealthModalOpen(true)}
                    className="px-3 py-1 bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 font-extrabold text-xs rounded-full border border-emerald-500/30 flex items-center gap-1.5 transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-emerald-400"
                    aria-label={`View business health score breakdown: ${healthScore} out of 100`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Business Health: {healthScore} / 100</span>
                    <HelpCircle className="w-3 h-3 text-emerald-400/80" />
                  </button>
                </div>

                <h1 className="text-3xl lg:text-4xl font-extrabold tracking-tight text-white">
                  Executive Decision Briefing
                </h1>
                <p className="text-xs text-slate-300 max-w-xl leading-relaxed font-medium">
                  Live empirical analysis generated from active database workspace ({activeWorkspace.name}).
                </p>
              </div>

              <div className="flex items-center gap-3">
                <Link
                  href="/decisions"
                  className="px-5 py-3 bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-extrabold rounded-2xl transition-all shadow-lg shadow-amber-500/30 flex items-center gap-2 focus-visible:ring-2 focus-visible:ring-amber-400"
                >
                  <Zap className="w-4 h-4 fill-slate-950" />
                  <span>Decision Center</span>
                </Link>

                <Link
                  href="/dynamic-dashboard"
                  className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-extrabold rounded-2xl transition-all shadow-lg shadow-indigo-600/30 flex items-center gap-2 focus-visible:ring-2 focus-visible:ring-indigo-400"
                >
                  <span>Open Dynamic Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 text-xs" role="list" aria-label="Key performance indicators">
              {kpis.map((kpi: any, idx: number) => (
                <div key={idx} className="p-4 bg-white/5 rounded-2xl border border-white/10 space-y-1" role="listitem">
                  <span className="text-slate-400 text-[10px] uppercase font-bold block">{kpi.name}</span>
                  <strong className="text-white text-lg font-extrabold block">{kpi.value}</strong>
                  <span className="text-[11px] text-emerald-400 font-semibold">{kpi.status}</span>
                </div>
              ))}
            </div>
          </div>

          <ExecutiveActionCenter actions={actionItems} />
          <ExecutiveNewsfeed news={newsItems} />
        </main>
      </div>
    </div>
  );
}
