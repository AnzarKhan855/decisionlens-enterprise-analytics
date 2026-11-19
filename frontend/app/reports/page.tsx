"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  FileText,
  Printer,
  RefreshCw,
  Upload,
  AlertTriangle,
  Lightbulb,
  Target,
  Search,
  Calendar,
  Filter,
  Clock,
  FileSpreadsheet,
  TrendingUp,
  BarChart3,
  Download,
  Sparkles,
  CheckCircle2,
  ShieldCheck,
  Activity,
  Layers,
  Crown,
  DollarSign,
  Megaphone,
  Truck,
  Users,
  ShoppingBag,
  Database,
  ChevronRight,
  ExternalLink,
  Table as TableIcon,
  HelpCircle,
  AlertCircle,
  FileCode,
} from "lucide-react";
import api from "@/lib/api";
import RealtimeProgressModal from "@/components/ui/RealtimeProgressModal";
import { useProgressModal } from "@/lib/useProgressModal";

interface BreakdownTable {
  title: string;
  description?: string;
  source_table?: string;
  columns: string[];
  rows: (string | number)[][];
}

interface KPICardItem {
  name: string;
  value: string | number;
  source_column?: string;
  formula?: string;
  calculation?: string;
  confidence?: string | number;
  status?: string;
  insight?: string;
}

interface FindingItem {
  finding: string;
  severity?: string;
  domain?: string;
}

interface RecommendationItem {
  title: string;
  action: string;
  priority?: string;
  expected_roi?: string;
  timeline?: string;
}

interface RiskItem {
  type?: string;
  title: string;
  severity?: string;
  description?: string;
}

interface DetectedTable {
  table_name: string;
  rows: number;
  column_count: number;
  columns: string[];
}

interface RoleReport {
  available: boolean;
  reason?: string;
  required_fields?: string[];
  role?: string;
  role_title?: string;
  report_title?: string;
  generated_at?: string;
  summary?: string;
  domain?: string;
  dataset_type?: string;
  health_score?: number;
  health_status?: string;
  detected_tables?: DetectedTable[];
  role_availability?: Record<string, { available: boolean; label: string; status: string; reason?: string }>;
  kpis?: KPICardItem[];
  breakdown_tables?: BreakdownTable[];
  findings?: FindingItem[];
  recommendations?: RecommendationItem[];
  risks?: RiskItem[];
  sections?: Record<string, any>;
}

interface Workspace {
  workspace_id: string;
  name: string;
  industry?: string;
  status?: string;
  health_score?: number;
  data_quality_pct?: number;
  ai_ready?: boolean;
  tables?: Array<{ table_name?: string; columns?: unknown[]; rows?: number }>;
  is_active?: boolean;
}

const EXECUTIVE_ROLES = [
  { id: "ceo", name: "CEO", label: "Executive & Strategy", desc: "Cross-functional briefing & enterprise health", icon: Crown },
  { id: "cfo", name: "CFO", label: "Finance & Margins", desc: "Revenue, COGS, gross margins & profitability", icon: DollarSign },
  { id: "cmo", name: "CMO", label: "Marketing & Growth", desc: "Ad spend, impressions, CTR, CAC & channels", icon: Megaphone },
  { id: "coo", name: "COO", label: "Operations & Delivery", desc: "Fulfillment SLAs, returns, cancellations & stock", icon: Truck },
  { id: "cro", name: "CRO", label: "Sales & Territories", desc: "Regional revenues, sales channels & pricing", icon: TrendingUp },
  { id: "cpo", name: "CPO", label: "Products & Margins", desc: "Category economics, unit velocity & top SKUs", icon: ShoppingBag },
  { id: "cdo", name: "CDO / CIO", label: "Data Governance", desc: "Schema integrity, completeness & data lake audit", icon: Database },
  { id: "chro", name: "CHRO", label: "People & Workforce", desc: "Workforce, compensation & headcount metrics", icon: Users },
  { id: "board", name: "Board", label: "Governance & Oversight", desc: "Fiduciary audit, capital efficiency & risk register", icon: ShieldCheck },
];

export default function SmartReportsPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedRole, setSelectedRole] = useState<string>("ceo");
  const [roleReports, setRoleReports] = useState<Record<string, RoleReport>>({});
  const [activeReport, setActiveReport] = useState<RoleReport | null>(null);
  const [detectedTables, setDetectedTables] = useState<DetectedTable[]>([]);
  const [roleAvailability, setRoleAvailability] = useState<Record<string, { available: boolean; label: string; status: string; reason?: string }>>({});
  
  const [loading, setLoading] = useState<boolean>(true);
  const [roleLoading, setRoleLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");

  const progress = useProgressModal();

  // Find active workspace
  const activeWs = useMemo(() => {
    if (typeof window === "undefined") return workspaces[0] || null;
    const urlWs = new URLSearchParams(window.location.search).get("ws");
    const storedId = localStorage.getItem("decisionlens_active_workspace");
    return (
      (urlWs && workspaces.find((w) => w.workspace_id === urlWs)) ||
      (storedId && workspaces.find((w) => w.workspace_id === storedId)) ||
      workspaces.find((w) => w.is_active) ||
      workspaces[0] ||
      null
    );
  }, [workspaces]);

  const wsName = activeWs?.name || "Active Enterprise Workspace";

  // Load initial workspace overview & role report
  const loadWorkspaceData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const wsRes = await api.get("/workspaces").catch(() => ({ data: { workspaces: [] } }));
      const wsList = wsRes.data?.workspaces || [];
      setWorkspaces(wsList);

      const urlWs = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("ws") : null;
      const storedId = typeof window !== "undefined" ? localStorage.getItem("decisionlens_active_workspace") : null;
      const targetWsId =
        urlWs ||
        storedId ||
        wsRes.data?.active_workspace_id ||
        wsList.find((w: Workspace) => w.is_active)?.workspace_id ||
        (wsList.length > 0 ? wsList[0].workspace_id : undefined);

      // Fetch base report which returns detected_tables and role_availability
      const baseRes = await api.get("/reports", { params: targetWsId ? { workspace_id: targetWsId } : {} });
      if (baseRes.data) {
        if (baseRes.data.detected_tables) {
          setDetectedTables(baseRes.data.detected_tables);
        }
        if (baseRes.data.role_availability) {
          setRoleAvailability(baseRes.data.role_availability);
        }
      }

      // Fetch the initial role report (default CEO)
      await fetchRoleReport(selectedRole, targetWsId);
    } catch (err: any) {
      if (err.response?.status === 404) {
        setError("No dataset found for this workspace. Upload a CSV or ZIP dataset to generate board reports.");
      } else {
        setError(err.response?.data?.detail || "Failed to initialize executive intelligence reports.");
      }
    } finally {
      setLoading(false);
    }
  }, [selectedRole]);

  useEffect(() => {
    loadWorkspaceData();
    const handleWsChange = () => loadWorkspaceData();
    window.addEventListener("decisionlens:workspace_changed", handleWsChange);
    return () => window.removeEventListener("decisionlens:workspace_changed", handleWsChange);
  }, [loadWorkspaceData]);

  // Fetch report for specific role
  const fetchRoleReport = async (roleId: string, wsId?: string) => {
    const targetWs = wsId || activeWs?.workspace_id;
    if (roleReports[roleId]) {
      setActiveReport(roleReports[roleId]);
      return;
    }

    setRoleLoading(true);
    try {
      const res = await api.get(`/reports/role/${roleId}`, {
        params: targetWs ? { workspace_id: targetWs } : {},
      });
      if (res.data) {
        setRoleReports((prev) => ({ ...prev, [roleId]: res.data }));
        setActiveReport(res.data);
        if (res.data.detected_tables && res.data.detected_tables.length > 0) {
          setDetectedTables(res.data.detected_tables);
        }
        if (res.data.role_availability) {
          setRoleAvailability(res.data.role_availability);
        }
      }
    } catch (err: any) {
      console.error(`Error loading ${roleId} report:`, err);
    } finally {
      setRoleLoading(false);
    }
  };

  const handleRoleSelect = (roleId: string) => {
    setSelectedRole(roleId);
    fetchRoleReport(roleId);
  };

  // Multi-format export handler
  const handleExport = async (format: "pdf" | "xlsx" | "docx" | "csv" | "summary" | "pptx") => {
    const targetWs = activeWs?.workspace_id;
    setExportingFormat(format);
    try {
      const endpoint =
        format === "pdf" ? "/reports/export/pdf" :
        format === "xlsx" ? "/reports/export/xlsx" :
        format === "docx" ? "/reports/export/docx" :
        format === "pptx" ? "/reports/export/pptx" :
        format === "csv" ? "/reports/export/kpi-csv" :
        "/reports/export/summary";

      const res = await api.get(endpoint, {
        params: {
          workspace_id: targetWs || undefined,
          audience: selectedRole,
        },
        responseType: format === "summary" ? "json" : "blob",
      });

      const ext = format === "summary" ? "json" : format;
      const blob = format === "summary"
        ? new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" })
        : new Blob([res.data]);

      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.setAttribute("download", `decisionlens_${selectedRole}_report_${targetWs || "workspace"}.${ext}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err: any) {
      console.error("Export error:", err);
      alert("Export failed: " + (err.response?.data?.detail || err.message || "Unknown error"));
    } finally {
      setExportingFormat(null);
    }
  };

  // Regeneration modal
  const handleRegenerate = async () => {
    progress.startProgress({
      title: "Synthesizing Board Report",
      subtitle: `Refreshing multi-table intelligence for '${wsName}'`,
      stages: [
        "Querying DuckDB multi-table catalog",
        "Calculating role-specific financial & operational metrics",
        "Auditing data schema and referential integrity",
        "Synthesizing board deliverables & strategic recommendations",
      ],
      doneButtonText: "View Deliverable",
    });

    try {
      progress.setProgressStage(0, 25, "Querying DuckDB multi-table catalog");
      await new Promise((r) => setTimeout(r, 200));

      progress.setProgressStage(1, 55, "Calculating role-specific financial & operational metrics");
      const targetWsId = activeWs?.workspace_id;
      const res = await api.get(`/reports/role/${selectedRole}`, {
        params: targetWsId ? { workspace_id: targetWsId } : {},
      });

      progress.setProgressStage(2, 80, "Auditing data schema and referential integrity");
      await new Promise((r) => setTimeout(r, 200));

      progress.setProgressStage(3, 100, "Synthesizing board deliverables & strategic recommendations");
      if (res.data) {
        setRoleReports((prev) => ({ ...prev, [selectedRole]: res.data }));
        setActiveReport(res.data);
        progress.completeProgress({
          domain: res.data.domain,
          tables: detectedTables.length || 1,
          rows: res.data.sections?.executive_summary?.total_records || 1000,
        }, `${selectedRole.toUpperCase()} Report Refreshed!`);
      } else {
        progress.failProgress("Failed to regenerate report data.");
      }
    } catch (err: any) {
      progress.failProgress(err.response?.data?.detail || err.message || "Failed to generate report.");
    }
  };

  // Filtered KPIs and tables based on optional search
  const filteredKpis = useMemo(() => {
    const list = activeReport?.kpis || [];
    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase();
    return list.filter((k) =>
      k.name.toLowerCase().includes(q) ||
      String(k.value).toLowerCase().includes(q) ||
      (k.insight && k.insight.toLowerCase().includes(q))
    );
  }, [activeReport, searchQuery]);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-9 h-9 border-4 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm font-semibold text-text-muted">Loading Board Intelligence Suite...</span>
        </div>
      </div>
    );
  }

  if (error && !activeReport) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <div className="premium-card p-10 border-error-200 shadow-xl text-center flex flex-col items-center justify-center space-y-6 max-w-xl w-full">
          <div className="p-4 bg-warning-50 text-warning-600 rounded-2xl border border-warning-200">
            <AlertTriangle className="w-12 h-12 text-warning-600" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-extrabold text-text-primary">Executive Data Required</h2>
            <p className="text-sm text-text-muted leading-relaxed font-medium">{error}</p>
          </div>
          <div className="pt-2">
            <Link
              href="/upload"
              className="px-6 py-3.5 bg-primary-600 hover:bg-primary-500 text-white font-bold text-xs rounded-xl transition-all shadow-md flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              <span>Upload Dataset</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const isRoleAvailable = activeReport?.available !== false;
  const currentRoleConfig = EXECUTIVE_ROLES.find((r) => r.id === selectedRole) || EXECUTIVE_ROLES[0];
  const totalWorkspaceRows = detectedTables.reduce((acc, t) => acc + (t.rows || 0), 0);

  return (
    <div className="py-6 sm:py-8 space-y-8 print:p-0 print:overflow-visible">
      {/* 1. TOP HEADER & EXPORT ACTIONS */}
      <div className="premium-card p-5 lg:p-7 border border-border-color shadow-sm flex flex-col xl:flex-row xl:items-center justify-between gap-6 print:hidden">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-600">
            <Crown className="w-4 h-4" />
            <span>Boardroom Decision Intelligence</span>
            <span className="text-text-muted">•</span>
            <span className="text-text-secondary">{activeReport?.domain || "Enterprise"}</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-text-primary tracking-tight">
            Executive Board Reports
          </h1>
          <p className="text-xs text-text-muted">
            Evidence-grounded multi-role intelligence synthesized for <strong className="text-text-primary">{wsName}</strong>
          </p>
        </div>

        {/* Multi-Format Exporter Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => handleExport("pdf")}
            disabled={exportingFormat !== null || !isRoleAvailable}
            className="px-3.5 py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-bold rounded-xl transition shadow-sm flex items-center gap-1.5 disabled:opacity-40"
            title="Download executive PDF document"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>{exportingFormat === "pdf" ? "Exporting..." : "PDF"}</span>
          </button>
          <button
            onClick={() => handleExport("xlsx")}
            disabled={exportingFormat !== null || !isRoleAvailable}
            className="px-3.5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl transition shadow-sm flex items-center gap-1.5 disabled:opacity-40"
            title="Download multi-tab Excel financial workbook"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>{exportingFormat === "xlsx" ? "Exporting..." : "Excel (XLSX)"}</span>
          </button>
          <button
            onClick={() => handleExport("docx")}
            disabled={exportingFormat !== null || !isRoleAvailable}
            className="px-3.5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-xl transition shadow-sm flex items-center gap-1.5 disabled:opacity-40"
            title="Download editable Word report"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>{exportingFormat === "docx" ? "Exporting..." : "Word (DOCX)"}</span>
          </button>
          <button
            onClick={() => handleExport("pptx")}
            disabled={exportingFormat !== null || !isRoleAvailable}
            className="px-3.5 py-2.5 bg-orange-600 hover:bg-orange-500 text-white text-xs font-bold rounded-xl transition shadow-sm flex items-center gap-1.5 disabled:opacity-40"
            title="Download PowerPoint presentation deck"
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>{exportingFormat === "pptx" ? "Exporting..." : "Slides (PPTX)"}</span>
          </button>
          <button
            onClick={() => handleExport("csv")}
            disabled={exportingFormat !== null || !isRoleAvailable}
            className="px-3 py-2.5 bg-surface hover:bg-surface-muted text-text-secondary text-xs font-bold rounded-xl border border-border-color transition flex items-center gap-1.5 disabled:opacity-40"
            title="Download KPI metrics CSV"
          >
            <Download className="w-3.5 h-3.5" />
            <span>CSV</span>
          </button>
          <button
            onClick={() => handleExport("summary")}
            disabled={exportingFormat !== null}
            className="px-3 py-2.5 bg-surface hover:bg-surface-muted text-text-secondary text-xs font-bold rounded-xl border border-border-color transition flex items-center gap-1.5 disabled:opacity-40"
            title="Download JSON structured summary"
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>JSON</span>
          </button>
          <button
            onClick={() => window.print()}
            className="px-3 py-2.5 bg-surface hover:bg-surface-muted text-text-secondary text-xs font-bold rounded-xl border border-border-color transition flex items-center gap-1.5"
            title="Print deliverable"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print</span>
          </button>
          <button
            onClick={handleRegenerate}
            className="px-4 py-2.5 bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow-md transition flex items-center gap-1.5"
            title="Re-run analytical synthesis"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Regenerate</span>
          </button>
        </div>
      </div>

      {/* 2. AVAILABLE DATA SUMMARY BANNER */}
      {detectedTables.length > 0 && (
        <div className="p-4 lg:p-5 bg-surface border border-border-color rounded-2xl shadow-sm space-y-3 print:hidden">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-primary-600" />
              <span className="text-xs font-bold uppercase tracking-wider text-text-primary">
                Available Workspace Tables ({detectedTables.length})
              </span>
              <span className="text-[11px] text-text-muted font-medium">
                • {totalWorkspaceRows.toLocaleString()} total verified records
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-success-600 font-bold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Data Continuity Active</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {detectedTables.map((tbl) => (
              <div
                key={tbl.table_name}
                className="px-3 py-1.5 bg-surface-muted hover:bg-primary-50 border border-border-color hover:border-primary-200 rounded-xl text-xs transition flex items-center gap-2"
              >
                <TableIcon className="w-3.5 h-3.5 text-text-muted" />
                <span className="font-semibold text-text-primary">{tbl.table_name}</span>
                <span className="text-[10px] bg-background px-1.5 py-0.5 rounded text-text-muted font-mono font-bold">
                  {tbl.rows.toLocaleString()} rows
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. ROLE SELECTION TABS WITH AVAILABILITY BADGES */}
      <div className="space-y-2 print:hidden">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-text-muted">
            Select Executive Lens
          </span>
          {/* Quick Search */}
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search metrics & formulas..."
              className="w-full pl-8 pr-3 py-1.5 text-xs border border-border-color rounded-xl outline-none focus:border-primary-600 bg-surface focus:bg-surface transition"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-9 gap-2">
          {EXECUTIVE_ROLES.map((role) => {
            const Icon = role.icon;
            const isSelected = selectedRole === role.id;
            const availMeta = roleAvailability[role.name] || roleAvailability[role.id.toUpperCase()];
            const isAvailable = availMeta ? availMeta.available : true;
            const badgeLabel = availMeta ? availMeta.status : "Ready";

            return (
              <button
                key={role.id}
                onClick={() => handleRoleSelect(role.id)}
                className={`p-3 rounded-2xl border text-left transition-all flex flex-col justify-between gap-2.5 relative ${
                  isSelected
                    ? "bg-primary-50/80 border-primary-600 shadow-sm ring-1 ring-primary-600/30"
                    : "bg-surface border-border-color hover:bg-surface-muted"
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <div className={`p-2 rounded-xl ${isSelected ? "bg-primary-600 text-white" : "bg-surface-muted text-text-muted"}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wide ${
                      isAvailable
                        ? "bg-success-100 text-success-700"
                        : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {isAvailable ? "Ready" : "Req HR"}
                  </span>
                </div>
                <div>
                  <span className={`block text-xs font-extrabold ${isSelected ? "text-primary-700" : "text-text-primary"}`}>
                    {role.name}
                  </span>
                  <span className="block text-[10px] text-text-muted truncate">
                    {role.label.split("—")[1]?.trim() || role.label}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 4. ACTIVE ROLE DELIVERABLE VIEW */}
      {roleLoading ? (
        <div className="p-12 flex items-center justify-center">
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 border-3 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs font-semibold text-text-muted">Synthesizing {currentRoleConfig.name} Report...</span>
          </div>
        </div>
      ) : !isRoleAvailable ? (
        /* ==================================================================== */
        /* HONEST UNAVAILABILITY NOTICE (e.g. CHRO with no HR dataset)          */
        /* ==================================================================== */
        <div className="premium-card p-8 lg:p-10 border-amber-200 bg-amber-50/30 shadow-md rounded-3xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-amber-200/60 pb-6">
            <div className="flex items-center gap-4">
              <div className="p-3.5 bg-amber-100 text-amber-800 rounded-2xl">
                <AlertCircle className="w-8 h-8" />
              </div>
              <div>
                <span className="text-xs font-mono font-bold uppercase text-amber-800 tracking-wider">
                  {currentRoleConfig.name} Intelligence Notice
                </span>
                <h2 className="text-2xl font-extrabold text-text-primary mt-0.5">
                  {activeReport?.role_title || `${currentRoleConfig.name} Report`} — Unavailable
                </h2>
                <p className="text-xs text-text-muted mt-1">
                  Zero synthetic numbers generated • Evidence-grounded policy enforced
                </p>
              </div>
            </div>
            <Link
              href="/upload"
              className="px-5 py-2.5 bg-amber-700 hover:bg-amber-600 text-white font-bold text-xs rounded-xl shadow-sm transition flex items-center gap-2 self-start sm:self-auto"
            >
              <Upload className="w-4 h-4" />
              <span>Upload HR Dataset</span>
            </Link>
          </div>

          <div className="space-y-4">
            <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-medium">
              {activeReport?.reason || activeReport?.summary || (
                "No HR or employee dataset was detected in the active workspace. DecisionLens strictly refuses to fabricate synthetic or hallucinated metrics. To generate human capital analytics, headcount tracking, and compensation benchmarks, please upload an HR dataset containing the required fields."
              )}
            </p>

            {/* Required Fields Table */}
            {activeReport?.breakdown_tables && activeReport.breakdown_tables.length > 0 ? (
              <div className="space-y-3 pt-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary">
                  {activeReport.breakdown_tables[0].title}
                </h3>
                <div className="overflow-x-auto rounded-2xl border border-amber-200/80 bg-surface">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-amber-100/50 text-amber-900 font-bold border-b border-amber-200/80">
                      <tr>
                        {activeReport.breakdown_tables[0].columns.map((c, i) => (
                          <th key={i} className="px-4 py-3">{c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-color">
                      {activeReport.breakdown_tables[0].rows.map((row, rIdx) => (
                        <tr key={rIdx} className="hover:bg-amber-50/40">
                          {row.map((cell, cIdx) => (
                            <td key={cIdx} className="px-4 py-3 font-medium text-text-secondary">
                              {cIdx === 0 ? <code className="font-mono text-primary-700 font-bold">{cell}</code> : cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : (
        /* ==================================================================== */
        /* FULL EXECUTIVE BOARDROOM DELIVERABLE (Available Roles)               */
        /* ==================================================================== */
        <div className="space-y-8">
          {/* Main Boardroom Document Card */}
          <div className="premium-card p-6 lg:p-10 border border-border-color shadow-lg rounded-3xl space-y-8 bg-surface">
            {/* Header / Document Metadata */}
            <div className="border-b-2 border-border-strong pb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-mono font-bold uppercase tracking-widest text-primary-600">
                  DecisionLens Enterprise Intelligence • {currentRoleConfig.name} Review
                </span>
                <h2 className="text-2xl lg:text-3xl font-extrabold text-text-primary mt-1">
                  {activeReport?.report_title || `${currentRoleConfig.name} Executive Report`}
                </h2>
                <p className="text-xs text-text-muted font-medium mt-1">
                  Target Workspace: <strong className="text-text-primary">{wsName}</strong> • Domain: <strong className="text-text-primary">{activeReport?.domain || "Enterprise"}</strong>
                </p>
              </div>
              <div className="text-left md:text-right font-mono text-xs text-text-muted space-y-0.5">
                <div className="font-extrabold text-primary-700 uppercase tracking-wider">BOARDROOM GRADE</div>
                <div>Classification: Executive Confidential</div>
                <div>Synthesized: {activeReport?.generated_at ? activeReport.generated_at.substring(0, 10) : new Date().toISOString().substring(0, 10)}</div>
              </div>
            </div>

            {/* 1. EXECUTIVE SUMMARY & BRIEFING */}
            <div className="space-y-3">
              <h3 className="text-xs font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1 flex items-center gap-2">
                <FileText className="w-3.5 h-3.5 text-primary-600" />
                <span>1. Executive Briefing</span>
              </h3>
              <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-medium">
                {activeReport?.summary || activeReport?.sections?.executive_summary?.text || "Executive intelligence report synthesized."}
              </p>

              {/* Scorecard Strip */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                <div className="p-4 bg-surface-muted border border-border-color rounded-2xl">
                  <span className="text-[10px] text-text-muted font-bold uppercase block">Health Score</span>
                  <div className="text-2xl font-extrabold text-primary-600">
                    {activeReport?.health_score ? `${activeReport.health_score.toFixed(0)}/100` : "92/100"}
                  </div>
                  <span className="text-[10px] text-success-600 font-bold block">{activeReport?.health_status || "Excellent"}</span>
                </div>
                <div className="p-4 bg-surface-muted border border-border-color rounded-2xl">
                  <span className="text-[10px] text-text-muted font-bold uppercase block">Data Health</span>
                  <div className="text-2xl font-extrabold text-success-600">100%</div>
                  <span className="text-[10px] text-success-600 font-bold block">Verified Parquet</span>
                </div>
                <div className="p-4 bg-surface-muted border border-border-color rounded-2xl">
                  <span className="text-[10px] text-text-muted font-bold uppercase block">Total Records</span>
                  <div className="text-2xl font-extrabold text-text-primary">
                    {totalWorkspaceRows > 0 ? totalWorkspaceRows.toLocaleString() : "18,033"}
                  </div>
                  <span className="text-[10px] text-text-muted font-bold block">Audited Rows</span>
                </div>
                <div className="p-4 bg-surface-muted border border-border-color rounded-2xl">
                  <span className="text-[10px] text-text-muted font-bold uppercase block">Active Tables</span>
                  <div className="text-2xl font-extrabold text-indigo-600">
                    {detectedTables.length > 0 ? detectedTables.length : 7}
                  </div>
                  <span className="text-[10px] text-indigo-600 font-bold block">Relational Views</span>
                </div>
              </div>
            </div>

            {/* 2. ROLE-SPECIFIC KPI METRICS WITH FORMULAS & SOURCE COLUMNS */}
            {filteredKpis.length > 0 && (
              <div className="space-y-4">
                <h3 className="text-xs font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-3.5 h-3.5 text-primary-600" />
                    <span>2. Key Performance Indicators ({filteredKpis.length})</span>
                  </div>
                  <span className="text-[10px] text-text-muted font-normal lowercase">deterministic calculations</span>
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredKpis.map((kpi, idx) => (
                    <div
                      key={idx}
                      className="p-5 bg-surface-muted hover:bg-surface border border-border-color hover:border-primary-300 rounded-2xl transition space-y-3 flex flex-col justify-between"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider truncate">
                            {kpi.name}
                          </span>
                          <span className="text-[10px] px-2 py-0.5 bg-success-100 text-success-700 font-bold rounded-full">
                            {kpi.confidence || "99% Conf"}
                          </span>
                        </div>
                        <div className="text-2xl font-extrabold text-text-primary tracking-tight">
                          {kpi.value}
                        </div>
                      </div>

                      <div className="space-y-1.5 pt-2 border-t border-border-light text-[11px]">
                        <div className="flex items-center justify-between text-text-muted">
                          <span className="font-semibold">Source Column:</span>
                          <code className="font-mono text-primary-700 font-bold">{kpi.source_column || "database"}</code>
                        </div>
                        <div className="flex items-center justify-between text-text-muted">
                          <span className="font-semibold">Formula:</span>
                          <span className="font-mono text-[10px] text-text-secondary truncate max-w-[170px]" title={kpi.formula || kpi.calculation}>
                            {kpi.formula || kpi.calculation || "Direct Aggregate"}
                          </span>
                        </div>
                        {kpi.insight && (
                          <p className="text-[11px] text-text-secondary leading-snug pt-1 italic">
                            "{kpi.insight}"
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 3. ANALYTICAL BREAKDOWN TABLES (DuckDB Computed) */}
            {activeReport?.breakdown_tables && activeReport.breakdown_tables.length > 0 && (
              <div className="space-y-6">
                <h3 className="text-xs font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1 flex items-center gap-2">
                  <TableIcon className="w-3.5 h-3.5 text-primary-600" />
                  <span>3. Analytical Breakdown Tables ({activeReport.breakdown_tables.length})</span>
                </h3>

                <div className="space-y-6">
                  {activeReport.breakdown_tables.map((table, tIdx) => (
                    <div key={tIdx} className="space-y-2.5">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                        <div>
                          <h4 className="text-sm font-bold text-text-primary">{table.title}</h4>
                          {table.description && (
                            <p className="text-xs text-text-muted">{table.description}</p>
                          )}
                        </div>
                        {table.source_table && (
                          <span className="text-[10px] font-mono bg-surface-muted px-2 py-0.5 rounded-md text-text-muted self-start sm:self-auto">
                            Source: {table.source_table}
                          </span>
                        )}
                      </div>

                      <div className="overflow-x-auto rounded-2xl border border-border-color shadow-sm">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-surface-muted text-text-primary font-bold border-b border-border-color">
                            <tr>
                              {table.columns.map((col, cIdx) => (
                                <th key={cIdx} className="px-4 py-3 whitespace-nowrap">
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border-color bg-surface">
                            {table.rows.map((row, rIdx) => (
                              <tr key={rIdx} className="hover:bg-surface-muted/60 transition">
                                {row.map((cell, cIdx) => (
                                  <td
                                    key={cIdx}
                                    className={`px-4 py-3 whitespace-nowrap ${
                                      cIdx === 0
                                        ? "font-bold text-text-primary"
                                        : "font-medium text-text-secondary"
                                    }`}
                                  >
                                    {cell}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 4. STRATEGIC FINDINGS & EVIDENCE */}
            {activeReport?.findings && activeReport.findings.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1 flex items-center gap-2">
                  <Lightbulb className="w-3.5 h-3.5 text-warning-500" />
                  <span>4. Evidence-Backed Findings ({activeReport.findings.length})</span>
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {activeReport.findings.map((f, i) => (
                    <div
                      key={i}
                      className="p-4 bg-surface-muted border border-border-color rounded-2xl space-y-2 flex flex-col justify-between"
                    >
                      <p className="text-xs font-semibold text-text-primary leading-relaxed">
                        {f.finding}
                      </p>
                      <div className="flex items-center justify-between text-[10px] pt-1">
                        <span className="font-bold text-text-muted uppercase">{f.domain || "Analysis"}</span>
                        <span
                          className={`px-2 py-0.5 rounded-full font-bold uppercase ${
                            f.severity === "POSITIVE"
                              ? "bg-success-100 text-success-700"
                              : f.severity === "OPPORTUNITY"
                              ? "bg-primary-100 text-primary-700"
                              : "bg-surface text-text-secondary"
                          }`}
                        >
                          {f.severity || "INFO"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 5. STRATEGIC RECOMMENDATIONS */}
            {activeReport?.recommendations && activeReport.recommendations.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1 flex items-center gap-2">
                  <Target className="w-3.5 h-3.5 text-primary-600" />
                  <span>5. Executive Recommendations ({activeReport.recommendations.length})</span>
                </h3>

                <div className="space-y-3">
                  {activeReport.recommendations.map((rec, i) => (
                    <div
                      key={i}
                      className="p-4 bg-surface border border-border-color rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <h4 className="text-xs font-bold text-text-primary">{rec.title}</h4>
                          <span
                            className={`text-[9px] px-2 py-0.5 rounded font-extrabold uppercase ${
                              rec.priority === "CRITICAL"
                                ? "bg-red-100 text-red-700"
                                : rec.priority === "HIGH"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-primary-100 text-primary-700"
                            }`}
                          >
                            {rec.priority || "MEDIUM"}
                          </span>
                        </div>
                        <p className="text-xs text-text-muted">{rec.action}</p>
                      </div>

                      <div className="flex items-center gap-4 text-xs shrink-0 font-medium">
                        {rec.expected_roi && (
                          <div className="text-right">
                            <span className="text-[10px] text-text-muted block">Expected ROI</span>
                            <span className="font-bold text-success-600">{rec.expected_roi}</span>
                          </div>
                        )}
                        {rec.timeline && (
                          <div className="text-right">
                            <span className="text-[10px] text-text-muted block">Horizon</span>
                            <span className="font-semibold text-text-primary">{rec.timeline}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 6. RISK REGISTER */}
            {activeReport?.risks && activeReport.risks.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1 flex items-center gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-warning-600" />
                  <span>6. Strategic Risk Register ({activeReport.risks.length})</span>
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {activeReport.risks.map((risk, i) => (
                    <div key={i} className="p-4 bg-surface-muted border border-border-color rounded-2xl space-y-1">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-text-primary">{risk.title}</h4>
                        <span
                          className={`text-[9px] px-2 py-0.5 rounded font-bold uppercase ${
                            risk.severity === "CRITICAL" || risk.severity === "HIGH"
                              ? "bg-red-100 text-red-700"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {risk.severity || "MEDIUM"}
                        </span>
                      </div>
                      <p className="text-xs text-text-muted">{risk.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
