"use client";

import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorState from "@/components/ui/ErrorState";
import {
  Activity,
  Search,
  Filter,
  Download,
  RefreshCw,
  Clock,
  User,
  Tag,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";

interface AuditLog {
  id?: string;
  timestamp?: string;
  user?: string;
  action?: string;
  workspace_id?: string;
  status?: string;
  affected_resource?: string;
  duration_ms?: number;
  details?: string;
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    fetchAuditLogs();
  }, []);

  async function fetchAuditLogs() {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get("/audit/logs", { params: { limit: 100 } });
      const logsData = Array.isArray(res.data) ? res.data : res.data.logs || [];
      setLogs(logsData);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load audit logs. Please check your connection.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  async function handleExportCSV() {
    try {
      const res = await api.get("/audit/export-csv", { responseType: "blob" });
      const blobUrl = window.URL.createObjectURL(new Blob([res.data], { type: "text/csv" }));
      const link = document.createElement("a");
      link.href = blobUrl;
      link.setAttribute("download", `audit_logs_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error("Failed to export audit logs CSV:", err);
    }
  }

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      !search ||
      (log.user || "").toLowerCase().includes(search.toLowerCase()) ||
      (log.action || "").toLowerCase().includes(search.toLowerCase()) ||
      (log.affected_resource || "").toLowerCase().includes(search.toLowerCase());
    const matchesAction = actionFilter === "all" || log.action === actionFilter;
    const matchesStatus = statusFilter === "all" || log.status === statusFilter;
    return matchesSearch && matchesAction && matchesStatus;
  });

  const actions = [...new Set(logs.map((l) => l.action).filter(Boolean))];
  const statuses = [...new Set(logs.map((l) => l.status).filter(Boolean))];

  function getStatusIcon(status?: string) {
    if (status === "SUCCESS" || status === "success") {
      return <CheckCircle2 className="w-4 h-4 text-success-500" />;
    }
    if (status === "FAILED" || status === "failed" || status === "ERROR") {
      return <XCircle className="w-4 h-4 text-error-500" />;
    }
    return <AlertTriangle className="w-4 h-4 text-warning-500" />;
  }

  function getStatusBadge(status?: string) {
    const s = (status || "UNKNOWN").toLowerCase();
    if (s === "success") {
      return "bg-success-50 text-success-700 border-success-200";
    }
    if (s === "failed" || s === "error") {
      return "bg-error-50 text-error-700 border-error-200";
    }
    return "bg-warning-50 text-warning-700 border-warning-200";
  }

  return (
    <div className="py-6 sm:py-8 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-widest text-primary-600 mb-1">
            <Activity className="w-4 h-4" aria-hidden="true" /> Audit Logs
          </div>
          <h1 className="text-2xl font-bold text-text-primary">Enterprise Audit Trail</h1>
          <p className="text-sm text-text-muted mt-1 font-medium">
            Monitor all actions, events, and access across the platform
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleExportCSV}
            className="px-4 py-2 bg-surface hover:bg-surface-muted text-text-primary text-xs font-bold rounded-xl border border-border-color transition-all flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            aria-label="Export audit logs to CSV"
          >
            <Download className="w-3.5 h-3.5" aria-hidden="true" />
            Export CSV
          </button>
          <button
            type="button"
            onClick={fetchAuditLogs}
            className="px-4 py-2 bg-background hover:bg-surface-muted text-text-primary text-xs font-bold rounded-xl transition-all flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            aria-label="Refresh audit logs"
          >
            <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-surface premium-card rounded-2xl border border-border-color p-4 flex flex-col md:flex-row md:items-center gap-4">
        <div className="flex-1 relative">
          <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
          <input
            type="text"
            placeholder="Search by user, action, or resource..."
            aria-label="Search by user, action, or resource"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-surface-muted border border-border-color rounded-xl text-xs text-text-primary placeholder:text-text-muted outline-none focus:border-primary-500 focus-visible:ring-2 focus-visible:ring-primary-500/20 transition-colors"
          />
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Tag className="w-3.5 h-3.5 text-text-muted" aria-hidden="true" />
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              aria-label="Filter audit logs by action"
              className="text-xs font-semibold text-text-primary bg-surface-muted border border-border-color rounded-lg px-3 py-2.5 outline-none cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500"
            >
              <option value="all">All Actions</option>
              {actions.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-text-muted" aria-hidden="true" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter audit logs by status"
              className="text-xs font-semibold text-text-primary bg-surface-muted border border-border-color rounded-lg px-3 py-2.5 outline-none cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500"
            >
              <option value="all">All Statuses</option>
              {statuses.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

          {/* Loading State */}
          {loading && (
            <div className="bg-surface rounded-2xl border border-border-color p-12 flex items-center justify-center">
              <LoadingSpinner label="Loading audit logs..." />
            </div>
          )}

          {/* Error State */}
          {!loading && error && (
            <div className="bg-surface rounded-2xl border border-border-color p-12">
              <ErrorState title="Failed to load audit logs" description={error} onRetry={fetchAuditLogs} retryLabel="Retry" />
            </div>
          )}

          {/* Logs Table */}
          {!loading && !error && (
            <div className="bg-surface premium-card rounded-2xl border border-border-color overflow-hidden">
              {filteredLogs.length === 0 ? (
                <div className="p-12 text-center">
                  <Activity className="w-12 h-12 text-text-muted mx-auto mb-3" />
                  <p className="text-sm text-text-muted font-medium">No audit log entries found.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="bg-surface-muted border-b border-border-color">
                        {["Timestamp", "User", "Action", "Resource", "Workspace", "Status", "Duration"].map(
                          (col) => (
                            <th
                              key={col}
                              className="px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-text-muted"
                            >
                              {col}
                            </th>
                          )
                        )}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredLogs.map((log, idx) => (
                        <tr key={idx} className="hover:bg-surface-muted transition-colors">
                          <td className="px-5 py-3 text-xs text-text-muted font-mono whitespace-nowrap">
                            {log.timestamp || "—"}
                          </td>
                          <td className="px-5 py-3 text-xs text-text-primary font-medium">
                            <div className="flex items-center gap-2">
                              <User className="w-3 h-3 text-text-muted" />
                              {log.user || "system"}
                            </div>
                          </td>
                          <td className="px-5 py-3 text-xs text-text-primary">
                            <span className="font-semibold">{log.action || "—"}</span>
                          </td>
                          <td className="px-5 py-3 text-xs text-text-secondary">
                            {log.affected_resource || "—"}
                          </td>
                          <td className="px-5 py-3 text-xs text-text-muted font-mono">
                            {log.workspace_id || "—"}
                          </td>
                          <td className="px-5 py-3 text-xs">
                            <span
                              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold border ${getStatusBadge(log.status)}`}
                            >
                              {getStatusIcon(log.status)}
                              {log.status || "UNKNOWN"}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-xs text-text-muted font-mono">
                            {log.duration_ms !== undefined ? `${log.duration_ms}ms` : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {filteredLogs.length > 0 && (
                <div className="px-5 py-3 border-t border-border-color bg-surface-muted flex items-center justify-between">
                  <span className="text-[10px] font-semibold text-text-muted">
                    Showing {filteredLogs.length} of {logs.length} entries
                  </span>
                </div>
              )}
            </div>
          )}
    </div>
  );
}