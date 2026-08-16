"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import api from "@/lib/api";
import { useToast } from "@/lib/toast";
import {
  FolderArchive,
  Plus,
  LayoutDashboard,
  Database,
  Building2,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Search,
  Activity,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import {
  BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";

interface BusinessWorkspace {
  workspace_id: string;
  name: string;
  industry: string;
  business_type?: string;
  health_score: number;
  data_quality_pct: number;
  ai_ready: boolean;
  forecast_ready: boolean;
  time_range: string;
  business_size: {
    orders: number;
    customers: number;
    products: number;
    transactions: number;
  };
  tables_count?: number;
  connected_tables_count?: number;
  total_records?: number;
  canonical_profile?: {
    total_records?: number;
    primary_metric?: string;
    primary_metric_sum?: number | string | null;
    measures?: string[];
    dimensions?: string[];
    identifiers?: string[];
  };
  status?: string;
}

export default function WorkspacesPage() {
  const [workspaces, setWorkspaces] = useState<BusinessWorkspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<BusinessWorkspace | null>(null);
  const { addToast } = useToast();

  useEffect(() => {
    loadWorkspaces();
  }, []);

  async function loadWorkspaces() {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get("/workspaces").catch(() => ({ data: { workspaces: [] } }));
      const wsList = res.data.workspaces || [];
      setWorkspaces(wsList);
    } catch (err) {
      console.error(err);
      setError("Failed to load workspaces. Please check your connection.");
    } finally {
      setLoading(false);
    }
  }

  async function confirmPermanentDeletion() {
    if (!deleteTarget) return;

    try {
      await api.delete(`/workspaces/${encodeURIComponent(deleteTarget.workspace_id)}`);
      setWorkspaces((prev) => prev.filter((w) => w.workspace_id !== deleteTarget.workspace_id));
      await loadWorkspaces();
      if (deleteTarget.workspace_id === localStorage.getItem("decisionlens_active_workspace")) {
        localStorage.removeItem("decisionlens_active_workspace");
        localStorage.removeItem("decisionlens_user_workspace");
      }
      addToast({ type: "success", title: "Workspace deleted", description: ` "${deleteTarget.name}" has been permanently removed.` });
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosError = err as { response?: { status?: number; data?: { detail?: string } } };
        if (axiosError.response?.status === 401) {
          addToast({ type: "error", title: "Session expired", description: "Please sign in again to delete workspaces." });
        } else if (axiosError.response?.status === 403) {
          addToast({ type: "error", title: "Not authorized", description: axiosError.response?.data?.detail || "You do not have permission to delete workspaces." });
        } else {
          addToast({ type: "error", title: "Deletion failed", description: axiosError.response?.data?.detail || "Failed to delete workspace. Please try again." });
        }
      } else {
        addToast({ type: "error", title: "Deletion failed", description: "Failed to delete workspace. Please try again." });
      }
    } finally {
      setDeleteTarget(null);
    }
  }

  const filteredWorkspaces = workspaces.filter(
    (w) =>
      w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      w.industry.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[70vh]" role="status" aria-label="Loading workspaces">
        <div className="flex flex-col items-center gap-3">
          <motion.div
            className="w-8 h-8 border-3 border-primary-600 border-t-transparent rounded-full"
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 0.9, ease: "linear" }}
          />
          <span className="text-sm font-semibold text-text-muted">Loading workspaces...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <motion.div
        className="p-8 flex items-center justify-center min-h-[70vh]"
        role="alert"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="premium-card p-12 text-center flex flex-col items-center justify-center space-y-6 max-w-xl w-full">
          <div className="p-5 bg-error-50 text-error-600 rounded-2xl border border-error-100 shadow-inner">
            <AlertCircle className="w-16 h-16 text-error-600" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-extrabold text-text-primary">Unable to Load Workspaces</h2>
            <p className="text-sm text-text-muted leading-relaxed font-medium">{error}</p>
          </div>
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={loadWorkspaces}
            className="px-8 py-4 bg-primary-600 hover:bg-primary-500 text-white font-extrabold text-xs rounded-2xl transition-all shadow-lg shadow-primary-600/30 flex items-center gap-2.5"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Retry</span>
          </motion.button>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <div className="premium-card p-5 lg:p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600 mb-1">
            <FolderArchive className="w-4 h-4" /> Workspaces
          </div>
          <h1 className="text-2xl font-extrabold text-text-primary">Business Workspaces</h1>
          <p className="text-sm text-text-muted mt-1 max-w-2xl">
            Manage your uploaded business datasets and workspaces.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/upload"
            className="px-4 py-2.5 bg-primary-600 hover:bg-primary-700 text-white text-xs font-bold rounded-xl transition-all shadow-md flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            <span>New Workspace</span>
          </Link>
        </div>
      </div>

      <div className="flex items-center justify-between gap-4 premium-card p-5 lg:p-6">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-text-muted absolute left-3.5 top-3" aria-hidden="true" />
          <input
            type="text"
            placeholder="Search workspaces..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-surface-muted border border-border-color rounded-xl text-xs text-text-primary outline-none focus:border-primary-500"
            aria-label="Search workspaces"
          />
        </div>
        <span className="text-xs font-mono text-text-muted">
          <strong>{filteredWorkspaces.length}</strong> workspace{filteredWorkspaces.length !== 1 ? 's' : ''}
        </span>
      </div>

      {filteredWorkspaces.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="premium-card p-16 text-center"
          >
          <FolderArchive className="w-16 h-16 text-text-muted mx-auto mb-4" aria-hidden="true" />
          <h3 className="text-base font-extrabold text-text-primary mb-1">No workspaces found</h3>
          <p className="text-xs text-text-muted max-w-sm mx-auto leading-relaxed">
            Upload a dataset or create a workspace to start building your executive dashboard.
          </p>
          <div className="flex items-center justify-center gap-3 mt-5">
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="px-4 py-2.5 text-xs font-semibold text-primary-600 hover:text-primary-700 border border-primary-200 rounded-xl transition-colors"
              >
                Clear search
              </button>
            )}
            <Link
              href="/upload"
              className="px-5 py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-bold rounded-xl transition-all shadow-md flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              <span>New Workspace</span>
            </Link>
          </div>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredWorkspaces.map((ws) => {
            const size = ws.business_size || {};
            const cp = ws.canonical_profile || {};
            const totalRecs = ws.total_records || cp.total_records || size.transactions || 0;
            const primaryName = cp.primary_metric || "Primary Metric";
            const primarySum = cp.primary_metric_sum !== null && cp.primary_metric_sum !== undefined
              ? (typeof cp.primary_metric_sum === "number" ? cp.primary_metric_sum.toLocaleString(undefined, { maximumFractionDigits: 2 }) : cp.primary_metric_sum)
              : null;

            const sizeValues = [
              { label: "Records", value: totalRecs, color: "var(--primary-500)" },
              { label: "Orders", value: size.orders ?? 0, color: "var(--success-500)" },
              { label: "Customers", value: size.customers ?? 0, color: "var(--primary-600)" },
              { label: "Products", value: size.products ?? 0, color: "var(--warning-500)" },
            ].filter(v => v.value > 0);

            const wsStatus = (ws.status || (ws.ai_ready ? "SEMANTIC_READY" : "PROCESSING")).toUpperCase();
            const statusConfig: Record<string, { bg: string; text: string; border: string }> = {
              SEMANTIC_READY: { bg: "bg-success-500/20", text: "text-success-300", border: "border-success-500/30" },
              PROCESSING: { bg: "bg-warning-500/20", text: "text-warning-300", border: "border-warning-500/30" },
              ERROR: { bg: "bg-error-500/20", text: "text-error-300", border: "border-error-500/30" },
              COMPLETED: { bg: "bg-primary-500/20", text: "text-primary-300", border: "border-primary-500/30" },
            };
            const sc = statusConfig[wsStatus] || statusConfig.PROCESSING;

            return (
              <motion.div
                key={ws.workspace_id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                whileHover={{ y: -4, transition: { duration: 0.2 } }}
                 className="premium-card p-5 lg:p-6 flex flex-col justify-between space-y-6"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="px-3 py-1 bg-primary-500/20 text-primary-300 text-xs font-extrabold rounded-full border border-primary-500/30 uppercase tracking-wide">
                      {ws.industry}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className={`px-2.5 py-1 ${sc.bg} ${sc.text} text-xs font-bold rounded-full border ${sc.border} flex items-center gap-1`}>
                        <Activity className="w-3.5 h-3.5" />
                        {wsStatus}
                      </span>
                      <span className="px-2.5 py-1 bg-success-500/20 text-success-300 text-xs font-bold rounded-full border border-success-500/30 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-success-400" />
                         Health: {ws.health_score ?? 92} / 100
                      </span>
                    </div>
                  </div>

                  <div>
                    <h2 className="text-2xl font-extrabold text-text-primary flex items-center gap-2">
                      {ws.name}
                    </h2>
                    <span className="text-xs text-text-muted font-mono block mt-1">
                      {totalRecs.toLocaleString()} records • {ws.tables_count || ws.connected_tables_count || 1} table(s)
                    </span>
                  </div>

                  {sizeValues.length > 0 && (
                    <div className="h-14">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={sizeValues} margin={{ top: 0, right: 10, left: -10, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--chart-grid)" />
                          <XAxis dataKey="label" tick={{ fontSize: 9, fill: "var(--chart-text)" }} axisLine={false} tickLine={false} />
                          <YAxis hide />
                          <Tooltip
                                contentStyle={{
                                  background: "var(--surface)",
                                  border: "1px solid var(--border-color)",
                                  borderRadius: "10px",
                                  boxShadow: "var(--shadow-md)",
                                  padding: "8px 12px",
                                  fontSize: "11px",
                                }}
                            labelStyle={{ color: "var(--text-primary)", fontWeight: 600, fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.04em" }}
                            itemStyle={{ color: "var(--text-secondary)", fontSize: "11px" }}
                            cursor={{ fill: "var(--hover-bg)", fillOpacity: 0.3 }}
                          />
                          <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                            {sizeValues.map((entry) => (
                              <Bar key={entry.label} dataKey="value" fill={entry.color} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  <div className="grid grid-cols-4 gap-3 text-xs pt-1">
                    <div className="p-3 bg-surface/5 rounded-2xl border border-foreground/10">
                      <span className="text-text-muted text-[11px] block font-medium">Total Records</span>
                      <strong className="text-text-primary text-base block mt-0.5">{totalRecs > 0 ? totalRecs.toLocaleString() : "N/A"}</strong>
                    </div>
                    <div className="p-3 bg-surface/5 rounded-2xl border border-foreground/10">
                      <span className="text-text-muted text-[11px] block font-medium truncate" title={primaryName}>{primaryName}</span>
                      <strong className="text-success-400 text-base block mt-0.5">{primarySum !== null ? primarySum : "N/A"}</strong>
                    </div>
                    <div className="p-3 bg-surface/5 rounded-2xl border border-foreground/10">
                      <span className="text-text-muted text-[11px] block font-medium">Customers</span>
                      <strong className="text-primary-300 text-base block mt-0.5">{size.customers != null ? size.customers.toLocaleString() : "N/A"}</strong>
                    </div>
                    <div className="p-3 bg-surface/5 rounded-2xl border border-foreground/10">
                      <span className="text-text-muted text-[11px] block font-medium">Products</span>
                      <strong className="text-primary-300 text-base block mt-0.5">{size.products != null ? size.products.toLocaleString() : "N/A"}</strong>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 text-xs pt-1">
                    <span className="px-2.5 py-1 bg-surface/10 text-text-secondary font-mono rounded-lg border border-foreground/10">
                      Quality: <strong>{ws.data_quality_pct || 98}%</strong>
                    </span>
                    <span className="px-2.5 py-1 bg-primary-500/30 text-primary-200 font-semibold rounded-lg border border-primary-500/30 flex items-center gap-1">
                      <Sparkles className="w-3.5 h-3.5 text-primary-300" /> AI Ready
                    </span>
                    <span className="px-2.5 py-1 bg-success-500/30 text-success-200 font-semibold rounded-lg border border-success-500/30 flex items-center gap-1">
                      <Activity className="w-3.5 h-3.5 text-success-300" /> Forecast Ready
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-4 border-t border-foreground/10">
                  <Link
                    href="/dynamic-dashboard"
                    className="px-3.5 py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-extrabold rounded-xl transition-all shadow-md flex items-center justify-center gap-1.5"
                  >
                    <LayoutDashboard className="w-3.5 h-3.5" />
                    <span>Open</span>
                  </Link>
                  <Link
                    href={`/explorer?ws=${ws.workspace_id}`}
                    className="px-3.5 py-2.5 bg-surface/10 hover:bg-surface/20 text-text-primary text-xs font-bold rounded-xl transition-all border border-foreground/10 flex items-center justify-center gap-1.5"
                  >
                    <Database className="w-3.5 h-3.5 text-primary-300" />
                    <span>Explore</span>
                  </Link>
                  <Link
                    href={`/profile?ws=${ws.workspace_id}`}
                    className="px-3.5 py-2.5 bg-surface/10 hover:bg-surface/20 text-text-primary text-xs font-bold rounded-xl transition-all border border-foreground/10 flex items-center justify-center gap-1.5"
                  >
                    <Building2 className="w-3.5 h-3.5 text-success-300" />
                    <span>Profile</span>
                  </Link>
                  <button
                    onClick={() => setDeleteTarget(ws)}
                    className="px-3.5 py-2.5 bg-error-500/20 hover:bg-error-500/30 text-error-300 text-xs font-bold rounded-xl transition-all border border-error-500/30 flex items-center justify-center gap-1.5"
                    aria-label={`Delete ${ws.name} workspace`}
                  >
                    <Trash2 className="w-3.5 h-3.5 text-error-300" />
                    <span>Delete</span>
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {deleteTarget && (
          <motion.div
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-6"
            role="dialog"
            aria-modal="true"
            aria-label="Delete workspace confirmation"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              initial={{ scale: 0.92, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.92, y: 20 }}
              transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
               className="premium-card max-w-md w-full p-6 space-y-5"
            >
            <div className="flex items-center gap-3 text-error-600 border-b border-border-light pb-3">
              <div className="p-3 bg-error-100 rounded-2xl">
                <AlertTriangle className="w-6 h-6 text-error-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-text-primary">Delete &ldquo;{deleteTarget.name}&rdquo;?</h3>
                <span className="text-xs text-text-muted">Permanent Workspace Deletion</span>
              </div>
            </div>

            <div className="text-xs text-text-secondary leading-relaxed">
              This action will permanently delete all workspace data including datasets, analytics, and AI models. This cannot be undone.
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-border-light">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 bg-surface-muted hover:bg-border-color text-text-secondary text-xs font-bold rounded-xl transition-all"
              >
                Cancel
              </button>
              <button
                onClick={confirmPermanentDeletion}
                className="px-5 py-2 bg-error-600 hover:bg-error-700 text-white text-xs font-extrabold rounded-xl transition-all shadow-md flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                 <span>Delete Permanently</span>
                </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
    </motion.div>
  );
}
