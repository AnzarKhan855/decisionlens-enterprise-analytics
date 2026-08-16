"use client";

import React, { useEffect, useState, useMemo } from "react";
import { motion } from "framer-motion";
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
  Star,
  Clock,
  FileSpreadsheet,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  TrendingUp,
  BarChart3,
} from "lucide-react";
import api, { API_BASE_URL } from "@/lib/api";
import type { MetricObject } from "@/lib/types";

function safeString(val: unknown): string {
  if (typeof val === "string") return val;
  if (val && typeof val === "object") {
    const obj = val as Record<string, unknown>;
    if (typeof obj.formatted_value === "string") return obj.formatted_value;
    if (typeof obj.value !== "undefined" && obj.value !== null) return safeString(obj.value);
    if (typeof obj.name === "string") return obj.name;
  }
  return String(val ?? "N/A");
}

function safeNumber(val: unknown): number {
  if (typeof val === "number") return val;
  if (typeof val === "string") {
    const cleaned = val.replace(/[^0-9.-]/g, "");
    const parsed = parseFloat(cleaned);
    return isNaN(parsed) ? 0 : parsed;
  }
  if (val && typeof val === "object") {
    const obj = val as Record<string, unknown>;
    if (typeof obj.value === "number") return obj.value;
    if (typeof obj.value === "string") {
      const cleaned = obj.value.replace(/[^0-9.-]/g, "");
      const parsed = parseFloat(cleaned);
      return isNaN(parsed) ? 0 : parsed;
    }
  }
  return 0;
}

interface ReportResponse {
  generated_at?: string;
  domain?: string;
  dataset_type?: string;
  workspace_name?: string;
  sections?: {
    executive_summary?: {
      text?: string;
      health_score?: number;
      health_status?: string;
      total_records?: number;
      domain?: string;
      primary_kpi?: string;
      available_kpis_count?: number;
    };
    kpi_overview?: Array<{
      name?: string;
      value?: string | number | MetricObject;
      source_column?: string;
      calculation?: string;
      confidence?: number | string | MetricObject;
      status?: string;
      insight?: string;
    }>;
    key_findings?: Array<Record<string, unknown>>;
    risks?: Array<Record<string, unknown>>;
    opportunities?: Array<Record<string, unknown>>;
    recommendations?: Array<Record<string, unknown>>;
    predictions?: Array<Record<string, unknown>>;
    roadmap_30_90_180?: {
      next_30_days?: Array<Record<string, unknown>>;
      next_90_days?: Array<Record<string, unknown>>;
      next_180_days?: Array<Record<string, unknown>>;
    };
    confidence_evidence?: Record<string, unknown>;
  };
  report_sections?: {
    executive_summary?: {
      text?: string;
      health_score?: number;
      health_status?: string;
      total_records?: number;
      domain?: string;
      primary_kpi?: string;
      available_kpis_count?: number;
    };
    kpi_overview?: Array<{
      name?: string;
      value?: string | number | MetricObject;
      source_column?: string;
      calculation?: string;
      confidence?: number | string | MetricObject;
      status?: string;
      insight?: string;
    }>;
    key_findings?: Array<Record<string, unknown>>;
    risks?: Array<Record<string, unknown>>;
    opportunities?: Array<Record<string, unknown>>;
    recommendations?: Array<Record<string, unknown>>;
    predictions?: Array<Record<string, unknown>>;
    roadmap_30_90_180?: {
      next_30_days?: Array<Record<string, unknown>>;
      next_90_days?: Array<Record<string, unknown>>;
      next_180_days?: Array<Record<string, unknown>>;
    };
    confidence_evidence?: Record<string, unknown>;
  };
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

const REPORT_TYPES = [
  { id: "all", label: "All Functions (Full Enterprise)" },
  { id: "ceo", label: "CEO — Executive & Strategy" },
  { id: "cfo", label: "CFO — Finance & Margins" },
  { id: "coo", label: "COO — Operations & Capacity" },
  { id: "cmo", label: "CMO — Customers & Growth" },
  { id: "executive", label: "Executive Summary" },
  { id: "kpi", label: "KPI Overview" },
  { id: "risk", label: "Risk Assessment" },
  { id: "forecast", label: "Forecasts" },
  { id: "recommendation", label: "Recommendations" },
];

const DATE_RANGES = [
  { id: "7d", label: "Last 7 days" },
  { id: "30d", label: "Last 30 days" },
  { id: "90d", label: "Last 90 days" },
  { id: "1y", label: "Last year" },
];

function PreviewThumbnail({ type }: { type?: string }) {
  const iconMap: Record<string, React.ReactNode> = {
    executive: <FileText className="w-6 h-6 text-primary-600" />,
    risk: <AlertTriangle className="w-6 h-6 text-warning-600" />,
    forecast: <TrendingUp className="w-6 h-6 text-success-600" />,
    recommendation: <Target className="w-6 h-6 text-primary-600" />,
    kpi: <BarChart3 className="w-6 h-6 text-primary-600" />,
  };
  const colorMap: Record<string, string> = {
    executive: "bg-primary-50 border-primary-100",
    risk: "bg-warning-50 border-warning-100",
    forecast: "bg-success-50 border-success-100",
    recommendation: "bg-primary-50 border-primary-100",
    kpi: "bg-primary-50 border-primary-100",
  };
  return (
    <div className={`w-full h-32 rounded-2xl border flex items-center justify-center ${colorMap[type || "executive"] || colorMap.executive}`}>
      {iconMap[type || "executive"] || iconMap.executive}
    </div>
  );
}

export default function SmartReportsPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState("all");
  const [dateRange, setDateRange] = useState("30d");
  const [favorites, setFavorites] = useState<Record<string, boolean>>({});
  const [recentSearches, setRecentSearches] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem("report_recent_searches");
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });

  useEffect(() => {
    fetchAll();
  }, []);

  async function fetchAll() {
    setLoading(true);
    setError(null);
    try {
      const wsRes = await api.get("/workspaces").catch(() => ({ data: { workspaces: [] } }));
      setWorkspaces(wsRes.data?.workspaces || []);

      const reportRes = await api.get("/reports");
      if (reportRes.data) {
        setReport(reportRes.data);
      } else {
        setError("Failed to load report data. Please try again.");
      }
    } catch (err: any) {
      if (err.response?.status === 404) {
        setError("No report data available yet. Upload a dataset to generate executive board reports.");
      } else {
        setError(err.response?.data?.detail || "Failed to load executive report for active workspace.");
      }
    } finally {
      setLoading(false);
    }
  }

  const activeWs = workspaces.find((w) => w.is_active) || workspaces[0];
  const wsName = activeWs?.name || "Active Workspace";
  const reportSections = report?.report_sections || report?.sections || (report as ReportResponse)?.sections;

  const getSeverityColor = (severity: string) => {
    const s = severity?.toUpperCase() || "LOW";
    if (s === "CRITICAL" || s === "HIGH") return "bg-error-100 text-error-700";
    if (s === "MEDIUM") return "bg-warning-100 text-warning-700";
    if (s === "WARNING") return "bg-warning-100 text-warning-700";
    return "bg-success-100 text-success-700";
  };

  const filteredSections = useMemo(() => {
    if (!reportSections) return [];
    const q = searchQuery.toLowerCase();
    const results: Array<{ key: string; title: string; type: string; data: Record<string, unknown> }> = [];

    const isFinancial = (text: string) => /revenue|cost|price|profit|margin|sales|budget|fee|tax|amount|salary|expense/i.test(text);
    const isOperational = (text: string) => /quantity|units|volume|count|capacity|downtime|defect|inventory|ship|deliver/i.test(text);
    const isCustomerMarket = (text: string) => /customer|user|client|patient|student|share|rating|churn|retention|conversion/i.test(text);

    if (reportSections.executive_summary) {
      const text = reportSections.executive_summary.text || "";
      if (["all", "ceo", "executive"].includes(selectedType) || (selectedType === "cfo" && isFinancial(text)) || (selectedType === "coo" && isOperational(text)) || (selectedType === "cmo" && isCustomerMarket(text))) {
        if (!q || text.toLowerCase().includes(q)) {
          results.push({ key: "exec", title: "Executive Summary", type: "executive", data: reportSections.executive_summary });
        }
      }
    }
    if (reportSections.kpi_overview?.length) {
      reportSections.kpi_overview.forEach((kpi: Record<string, unknown>, i: number) => {
        const name = (kpi.name as string || "").toLowerCase();
        const value = (kpi.value as string || "").toLowerCase();
        const matchesQuery = !q || name.includes(q) || value.includes(q);

        let matchesRole = true;
        if (selectedType === "cfo") matchesRole = isFinancial(name);
        else if (selectedType === "coo") matchesRole = isOperational(name);
        else if (selectedType === "cmo") matchesRole = isCustomerMarket(name);
        else if (selectedType === "kpi") matchesRole = true;
        else if (selectedType !== "all" && selectedType !== "ceo") matchesRole = selectedType === "kpi";

        if (matchesQuery && matchesRole) {
          results.push({ key: `kpi-${i}`, title: (kpi.name as string) || `KPI ${i+1}`, type: "kpi", data: kpi });
        }
      });
    }
    if (reportSections.key_findings?.length) {
      reportSections.key_findings.forEach((f: Record<string, unknown>, i: number) => {
        const title = (f.agent as string) || (f.title as string) || `Finding ${i + 1}`;
        const detail = (f.finding as string) || (f.detail as string) || "";
        const combined = `${title} ${detail}`.toLowerCase();
        const matchesQuery = !q || title.toLowerCase().includes(q) || detail.toLowerCase().includes(q);

        let matchesRole = true;
        if (selectedType === "cfo") matchesRole = isFinancial(combined);
        else if (selectedType === "coo") matchesRole = isOperational(combined);
        else if (selectedType === "cmo") matchesRole = isCustomerMarket(combined);
        else if (selectedType === "executive" || selectedType === "ceo" || selectedType === "all") matchesRole = true;
        else matchesRole = false;

        if (matchesQuery && matchesRole) {
          results.push({ key: `finding-${i}`, title, type: "executive", data: f });
        }
      });
    }
    if (reportSections.risks?.length) {
      reportSections.risks.forEach((r: Record<string, unknown>, i: number) => {
        const title = (r.title as string) || `Risk ${i + 1}`;
        const desc = (r.description as string) || "";
        const combined = `${title} ${desc}`.toLowerCase();
        const matchesQuery = !q || title.toLowerCase().includes(q);

        let matchesRole = true;
        if (selectedType === "cfo") matchesRole = isFinancial(combined);
        else if (selectedType === "coo") matchesRole = isOperational(combined);
        else if (selectedType === "cmo") matchesRole = isCustomerMarket(combined);
        else if (["all", "ceo", "risk"].includes(selectedType)) matchesRole = true;

        if (matchesQuery && matchesRole) {
          results.push({ key: `risk-${i}`, title, type: "risk", data: r });
        }
      });
    }
    if (reportSections.recommendations?.length) {
      reportSections.recommendations.forEach((r: Record<string, unknown>, i: number) => {
        const title = (r.title as string) || (r.recommendation as string) || `Recommendation ${i + 1}`;
        const action = (r.suggested_action as string) || "";
        const combined = `${title} ${action}`.toLowerCase();
        const matchesQuery = !q || title.toLowerCase().includes(q);

        let matchesRole = true;
        if (selectedType === "cfo") matchesRole = isFinancial(combined);
        else if (selectedType === "coo") matchesRole = isOperational(combined);
        else if (selectedType === "cmo") matchesRole = isCustomerMarket(combined);
        else if (["all", "ceo", "recommendation"].includes(selectedType)) matchesRole = true;

        if (matchesQuery && matchesRole) {
          results.push({ key: `rec-${i}`, title, type: "recommendation", data: r });
        }
      });
    }
    if (reportSections.predictions?.length) {
      reportSections.predictions.forEach((p: Record<string, unknown>, i: number) => {
        const title = (p.model_type as string) || (p.metric as string) || `Forecast ${i + 1}`;
        const impact = (p.business_impact as string) || "";
        const combined = `${title} ${impact}`.toLowerCase();
        const matchesQuery = !q || title.toLowerCase().includes(q);

        let matchesRole = true;
        if (selectedType === "cfo") matchesRole = isFinancial(combined);
        else if (selectedType === "coo") matchesRole = isOperational(combined);
        else if (selectedType === "cmo") matchesRole = isCustomerMarket(combined);
        else if (["all", "ceo", "forecast"].includes(selectedType)) matchesRole = true;

        if (matchesQuery && matchesRole) {
          results.push({ key: `pred-${i}`, title, type: "forecast", data: p });
        }
      });
    }

    return results;
  }, [reportSections, searchQuery, selectedType]);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (query.trim()) {
      setRecentSearches((prev) => {
        const next = [query, ...prev.filter((s) => s !== query)].slice(0, 10);
        localStorage.setItem("report_recent_searches", JSON.stringify(next));
        return next;
      });
    }
  };

  const toggleFavorite = (key: string) => {
    setFavorites((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]" role="status" aria-label="Loading report">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm font-semibold text-text-muted">Loading Executive Report...</span>
        </div>
      </div>
    );
  }

  if (error || !reportSections) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]" role="alert">
        <div className="premium-card p-12 border-error-200 shadow-lg text-center flex flex-col items-center justify-center space-y-6 max-w-xl w-full">
          <div className="p-5 bg-warning-50 text-warning-600 rounded-2xl border border-warning-100 shadow-inner">
            <AlertTriangle className="w-16 h-16 text-warning-600" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-extrabold text-text-primary">Report Unavailable</h2>
            <p className="text-sm text-text-muted leading-relaxed font-medium">
              {error || "No executive report sections found. Please upload a dataset to generate board reports."}
            </p>
          </div>
          <div className="pt-2 flex gap-3">
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

  const execSummary = reportSections.executive_summary || {
    text: "Upload a dataset to generate an evidence-grounded executive report.",
    health_score: null,
    health_status: "No Data",
    total_records: 0,
    domain: "Generic Business",
    primary_kpi: "N/A",
    available_kpis_count: 0,
  };
  const kpis: Array<{ name?: string; value?: string | number | MetricObject; source_column?: string; calculation?: string; confidence?: string | number | MetricObject; status?: string; insight?: string }> = reportSections.kpi_overview || [];
  const findings: Array<Record<string, unknown>> = reportSections.key_findings || [];
  const risks: Array<Record<string, unknown>> = reportSections.risks || [];
  const opportunities: Array<Record<string, unknown>> = reportSections.opportunities || [];
  const recommendations: Array<Record<string, unknown>> = reportSections.recommendations || [];
  const predictions: Array<Record<string, unknown>> = reportSections.predictions || [];
  const roadmap = reportSections.roadmap_30_90_180 || { next_30_days: [], next_90_days: [], next_180_days: [] };

  return (
    <div className="p-8 space-y-8 print:p-0 print:overflow-visible">
      {/* Header */}
      <div className="premium-card p-5 lg:p-6 border border-border-color shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 print:hidden">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600 mb-1">
            <FileText className="w-4 h-4" /> Executive Intelligence Report
          </div>
          <h1 className="text-2xl font-bold text-text-primary">Board-Ready Enterprise Report</h1>
          <p className="text-sm text-text-muted mt-1">
            Generated for {wsName} on {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => window.print()}
            className="px-5 py-2.5 bg-background hover:bg-surface-muted text-text-primary text-xs font-bold rounded-xl transition-all shadow-md flex items-center gap-2"
            aria-label="Print or download report as PDF"
          >
            <Printer className="w-4 h-4 text-primary-400" />
            <span>Print / PDF</span>
          </button>
          <button
            onClick={fetchAll}
            className="px-4 py-2.5 bg-surface hover:bg-surface-muted text-text-secondary text-xs font-bold rounded-xl border border-border-color transition-all flex items-center gap-2"
            aria-label="Refresh report data"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Sidebar Filters */}
        <motion.aside
          animate={{ width: sidebarOpen ? 280 : 0, opacity: sidebarOpen ? 1 : 0 }}
          transition={{ duration: 0.3 }}
          className="hidden lg:block premium-card border border-border-color shadow-sm overflow-hidden"
        >
          <div className="p-4 border-b border-border-light flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-text-primary uppercase tracking-wider">
              <SlidersHorizontal className="w-4 h-4 text-primary-600" />
              <span>Filters</span>
            </div>
            <button onClick={() => setSidebarOpen(false)} className="text-text-muted hover:text-text-secondary">
              <ChevronLeft className="w-4 h-4" />
            </button>
          </div>

          <div className="p-4 space-y-5">
            {/* Search */}
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Search Reports</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Search keywords..."
                  className="w-full pl-8 pr-3 py-2 text-xs border border-border-color rounded-xl outline-none focus:border-primary-600 bg-surface-muted focus:bg-surface transition"
                />
              </div>
              {recentSearches.length > 0 && (
                <div className="space-y-1">
                  <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Recent</span>
                  {recentSearches.slice(0, 5).map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSearch(s)}
                      className="flex items-center gap-1.5 text-[11px] text-text-secondary hover:text-primary-600 transition"
                    >
                      <Clock className="w-3 h-3" /> {s}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Date Range */}
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Date Range</label>
              <div className="space-y-1">
                {DATE_RANGES.map((dr) => (
                  <button
                    key={dr.id}
                    onClick={() => setDateRange(dr.id)}
                    className={`w-full text-left px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                      dateRange === dr.id
                        ? "bg-primary-50 text-primary-700 border border-primary-200"
                        : "border border-transparent hover:bg-surface-muted text-text-secondary"
                    }`}
                  >
                    <Calendar className="w-3 h-3 inline mr-1.5" />
                    {dr.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Report Type */}
            <div className="space-y-2">
              <label className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Report Type</label>
              <div className="space-y-1">
                {REPORT_TYPES.map((rt) => (
                  <button
                    key={rt.id}
                    onClick={() => setSelectedType(rt.id)}
                    className={`w-full text-left px-3 py-2 rounded-xl text-xs font-medium transition-all ${
                      selectedType === rt.id
                        ? "bg-primary-50 text-primary-700 border border-primary-200"
                        : "border border-transparent hover:bg-surface-muted text-text-secondary"
                    }`}
                  >
                    <Filter className="w-3 h-3 inline mr-1.5" />
                    {rt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </motion.aside>

        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="hidden lg:block absolute left-4 top-24 z-20 bg-surface border border-border-color rounded-r-xl p-2 text-text-secondary hover:text-primary-600 shadow-sm"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}

        {/* Main Report Content */}
        <div className="flex-1 min-w-0 space-y-8">
          {/* Filter bar */}
          <div className="premium-card p-4 border border-border-color shadow-sm flex items-center gap-3 print:hidden">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder="Search report sections..."
                className="w-full pl-9 pr-4 py-2.5 text-sm border border-border-color rounded-xl outline-none focus:border-primary-600 bg-surface-muted focus:bg-surface transition"
              />
            </div>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="px-3 py-2.5 text-sm border border-border-color rounded-xl bg-surface-muted outline-none focus:border-primary-600"
            >
              {REPORT_TYPES.map((rt) => (
                <option key={rt.id} value={rt.id}>{rt.label}</option>
              ))}
            </select>
          </div>

          {/* Report Cards Grid */}
          {filteredSections.length === 0 ? (
            <div className="premium-card p-12 border border-border-color shadow-lg text-center space-y-4">
              <div className="p-4 bg-surface-muted text-text-muted rounded-2xl inline-block">
                <Search className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-text-primary">No Results Found</h3>
              <p className="text-sm text-text-muted">Try adjusting your search query or filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredSections.map((item) => (
                <motion.div
                  key={item.key}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="premium-card border border-border-color shadow-sm hover:shadow-md transition-all overflow-hidden flex flex-col"
                >
                  <div className="p-4 border-b border-border-light flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <PreviewThumbnail type={item.type} />
                      <div>
                        <h3 className="text-sm font-bold text-text-primary">{item.title}</h3>
                        <span className="text-[10px] font-mono text-text-muted uppercase">{item.type}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => toggleFavorite(item.key)}
                        className={`p-1.5 rounded-lg transition-colors ${
                          favorites[item.key] ? "text-warning-500 bg-warning-50" : "text-text-muted hover:text-text-secondary hover:bg-surface-muted"
                        }`}
                      >
                        <Star className={`w-4 h-4 ${favorites[item.key] ? "fill-current" : ""}`} />
                      </button>
                      {favorites[item.key] && (
                        <span className="text-[10px] font-bold text-warning-600 uppercase tracking-wider">Favorite</span>
                      )}
                    </div>
                  </div>
                  <div className="p-4 flex-1">
                    {item.type === "executive" && (
                      <p className="text-xs text-text-secondary leading-relaxed line-clamp-3">{(item.data as Record<string, unknown>).text as string}</p>
                    )}
                    {item.type === "kpi" && (
                      <div className="space-y-2">
                        <p className="text-lg font-bold text-text-primary">{safeString((item.data as Record<string, unknown>).value)}</p>
                        <p className="text-[11px] text-text-muted">Source: {safeString((item.data as Record<string, unknown>).source_column)}</p>
                        <p className="text-[11px] text-text-muted">Formula: {safeString((item.data as Record<string, unknown>).calculation)}</p>
                      </div>
                    )}
                    {item.type === "risk" && (
                      <div className="space-y-2">
                        <p className="text-xs text-text-secondary">{(item.data as Record<string, unknown>).explanation as string || (item.data as Record<string, unknown>).business_impact as string || "Risk assessment pending."}</p>
                        <span className={`inline-flex px-2 py-0.5 rounded-lg text-[10px] font-bold ${getSeverityColor(((item.data as Record<string, unknown>).severity as string) || "LOW")}`}>
                          {(item.data as Record<string, unknown>).severity as string}
                        </span>
                      </div>
                    )}
                    {item.type === "recommendation" && (
                      <div className="space-y-2">
                        <p className="text-xs text-text-secondary">{(item.data as Record<string, unknown>).rationale as string}</p>
                        <span className="inline-flex px-2 py-0.5 bg-primary-50 text-primary-700 rounded-lg text-[10px] font-bold">
                          {(item.data as Record<string, unknown>).priority as string || "HIGH"}
                        </span>
                      </div>
                    )}
                    {item.type === "forecast" && (
                      <div className="space-y-2">
                        <p className="text-xs text-text-secondary">{(item.data as Record<string, unknown>).prediction as string || (item.data as Record<string, unknown>).model_used as string}</p>
                        <span className="inline-flex px-2 py-0.5 bg-success-50 text-success-700 rounded-lg text-[10px] font-bold">
                          {(item.data as Record<string, unknown>).confidence as string || "High"} Confidence
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="p-4 border-t border-border-light flex items-center gap-2">
                    <button
                      onClick={() => window.print()}
                       className="text-[11px] px-3 py-1.5 bg-background text-text-primary rounded-xl font-semibold hover:bg-surface-muted transition flex items-center gap-1"
                    >
                      <FileSpreadsheet className="w-3 h-3" />
                      Export
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          )}

          {/* Report Details Section */}
          <div className="premium-card p-6 lg:p-8 border border-border-color shadow-lg max-w-4xl mx-auto space-y-8 print:border-none print:shadow-none print:p-0">
            <div className="border-b-2 border-border-strong pb-6 flex items-center justify-between">
              <div>
                <span className="text-xs font-mono font-bold uppercase tracking-widest text-primary-600">DecisionLens Enterprise Intelligence</span>
                <h1 className="text-2xl font-extrabold text-text-primary mt-1">Executive Summary</h1>
                <p className="text-xs text-text-muted font-medium mt-0.5">Live report for {wsName}</p>
              </div>
              <div className="text-right font-mono text-xs text-text-muted">
                <div className="font-extrabold text-text-primary">CONFIDENTIAL</div>
                <div>Classification: Internal Use Only</div>
                <div>Generated: {new Date().toISOString().split("T")[0]}</div>
              </div>
            </div>

            <div className="space-y-3">
              <h2 className="text-sm font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1">
                1. Executive Summary
              </h2>
              <p className="text-xs text-text-secondary leading-relaxed font-medium">{execSummary.text}</p>
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div className="p-4 bg-surface-muted border border-border-color rounded-2xl space-y-1">
                  <span className="text-[10px] text-text-muted font-bold uppercase block">Workspace</span>
                  <strong className="text-lg font-extrabold text-text-primary block">{wsName}</strong>
                  <span className="text-[11px] text-success-600 font-bold block">
                    {activeWs?.status === "SEMANTIC_READY" || activeWs?.status === "COMPLETED" ? "Active" : "Ready"}
                  </span>
                </div>
                <div className="p-4 bg-surface-muted border border-border-color rounded-2xl space-y-1">
                  <span className="text-[10px] text-text-muted font-bold uppercase block">Domain</span>
                  <strong className="text-lg font-extrabold text-text-primary block">{execSummary.domain}</strong>
                  <span className="text-[11px] text-success-600 font-bold block">
                    {activeWs?.ai_ready ? "AI Verified" : "Analyzed"}
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h2 className="text-sm font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1">
                2. Enterprise Health Overview
              </h2>
              <div className="grid grid-cols-3 gap-4">
                <div className="p-5 bg-surface border border-border-color rounded-2xl text-center">
                  <div className="text-3xl font-extrabold text-primary-600">{execSummary.health_score ?? "N/A"}/100</div>
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mt-2">Health Score</div>
                </div>
                <div className="p-5 bg-surface border border-border-color rounded-2xl text-center">
                  <div className="text-3xl font-extrabold text-success-600">
                    {activeWs?.data_quality_pct ?? execSummary.health_score}%
                  </div>
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mt-2">Data Quality</div>
                </div>
                <div className="p-5 bg-surface border border-border-color rounded-2xl text-center">
                  <div className="text-3xl font-extrabold text-warning-500">
                    {execSummary.health_status?.charAt(0) || "A"}
                  </div>
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mt-2">Grade</div>
                </div>
              </div>
            </div>

            {kpis.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-sm font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1">
                  3. Key Performance Indicators
                </h2>
                <div className="grid grid-cols-2 gap-4 text-xs">
                  {kpis.map((kpi, idx) => (
                    <div key={idx} className="p-4 bg-surface-muted border border-border-color rounded-2xl space-y-1">
                      <span className="text-[10px] text-text-muted font-bold uppercase block">{safeString(kpi.name)}</span>
                      <strong className="text-lg font-extrabold text-text-primary block">{safeString(kpi.value)}</strong>
                      <span className="text-[11px] text-text-muted font-mono block">Source: {safeString(kpi.source_column)}</span>
                      <span className="text-[11px] text-text-muted block">Formula: {safeString(kpi.calculation)}</span>
                      <span className="text-[11px] text-success-600 font-bold block">{safeNumber(kpi.confidence)}% Confidence</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {findings.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-sm font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1">
                  4. Key Findings
                </h2>
                <div className="space-y-3">
                  {findings.map((finding: Record<string, unknown>, idx: number) => (
                    <div key={idx} className="flex items-start gap-3 p-4 bg-surface-muted rounded-2xl border border-border-color">
                      <div className="w-8 h-8 rounded-xl bg-primary-100 text-primary-600 flex items-center justify-center flex-shrink-0">
                        <Lightbulb className="w-4 h-4" />
                      </div>
                      <div className="space-y-1">
                        <h3 className="text-xs font-bold text-text-primary">
                          {(finding.agent as string) || (finding.title as string) || `Finding ${idx + 1}`}
                        </h3>
                        <p className="text-[11px] text-text-muted leading-relaxed">
                          {(finding.finding as string) || (finding.detail as string) || JSON.stringify(finding)}
                        </p>
                        {(finding.recommendation as string) && (
                          <p className="text-[11px] text-primary-600 font-medium">{finding.recommendation as string}</p>
                        )}
                        <div className="flex items-center gap-3 mt-2">
                          {(finding.focus as string) && (
                            <span className="text-[10px] font-mono font-bold text-text-secondary bg-surface-muted px-2 py-0.5 rounded">
                              {finding.focus as string}
                            </span>
                          )}
                          {(finding.confidence as string) && (
                            <span className="text-[10px] font-mono font-bold text-success-600 bg-success-50 px-2 py-0.5 rounded">
                              {finding.confidence as string} CONFIDENCE
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {risks.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-sm font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1">
                  5. Risk Assessment Matrix
                </h2>
                <div className="table-wrapper overflow-x-auto">
                  <table className="w-full text-left table-striped" aria-label="Risk assessment matrix">
                    <thead>
                      <tr className="bg-background text-text-primary">
                        {["Risk", "Type", "Severity", "Period", "Impact", "Mitigation", "Status"].map((col) => (
                          <th key={col} className="px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {risks.map((risk: Record<string, unknown>, idx: number) => (
                        <tr key={idx} className="hover:bg-surface-muted">
                          <td className="px-3 py-2.5 text-xs font-medium text-text-primary max-w-[200px]">
                            {risk.title as string}
                          </td>
                          <td className="px-3 py-2.5 text-xs text-text-secondary">
                            {(risk.type as string) || "General"}
                          </td>
                          <td className="px-3 py-2.5 text-xs">
                            <span className={`px-2 py-0.5 rounded-lg text-[10px] font-bold ${getSeverityColor(risk.severity as string)}`}>
                              {risk.severity as string}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 text-xs text-text-secondary">
                            {risk.period as string}
                          </td>
                          <td className="px-3 py-2.5 text-xs text-text-secondary max-w-[200px]">
                            {(risk.explanation as string) || (risk.business_impact as string) || "Impact assessment pending."}
                          </td>
                          <td className="px-3 py-2.5 text-xs text-text-secondary max-w-[200px]">
                            {(risk.possible_causes as string[])?.[0] || "Review data trends"}
                          </td>
                          <td className="px-3 py-2.5 text-xs">
                            <span className="px-2 py-0.5 bg-info-100 text-info-700 rounded-lg text-[10px] font-bold">Monitoring</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {opportunities.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-sm font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1">
                  6. Opportunities
                </h2>
                <div className="space-y-3">
                  {opportunities.map((opp: Record<string, unknown>, idx: number) => (
                    <div key={idx} className="flex items-start gap-3 p-4 bg-surface-muted rounded-2xl border border-border-color">
                      <div className="w-8 h-8 rounded-xl bg-success-100 text-success-600 flex items-center justify-center flex-shrink-0">
                        <Target className="w-4 h-4" />
                      </div>
                      <div>
                        <h3 className="text-xs font-bold text-text-primary">{opp.title as string}</h3>
                        <p className="text-[11px] text-text-muted mt-0.5">{opp.description as string}</p>
                        <div className="flex items-center gap-3 mt-2">
                          <span className="text-[10px] font-mono font-bold text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                            {opp.metric as string}
                          </span>
                          <span className="text-[10px] font-mono font-bold text-success-600 bg-success-50 px-2 py-0.5 rounded">
                            {opp.confidence as number}% CONFIDENCE
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {recommendations.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-sm font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1">
                  7. Strategic Recommendations
                </h2>
                <div className="space-y-3">
                  {recommendations.map((rec: Record<string, unknown>, idx: number) => (
                    <div key={idx} className="flex items-start gap-3 p-4 bg-surface-muted rounded-2xl border border-border-color">
                      <div className="w-8 h-8 rounded-xl bg-primary-100 text-primary-600 flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-bold">{idx + 1}</span>
                      </div>
                      <div>
                        <h3 className="text-xs font-bold text-text-primary">{rec.title as string}</h3>
                        <p className="text-[11px] text-text-muted mt-0.5">{rec.rationale as string}</p>
                        <div className="flex items-center gap-3 mt-2">
                          <span className="text-[10px] font-mono font-bold text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                            {(rec.priority as string) || "HIGH"}
                          </span>
                          <span className="text-[10px] font-mono font-bold text-success-600 bg-success-50 px-2 py-0.5 rounded">
                            {rec.confidence as string} CONFIDENCE
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {predictions.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-sm font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1">
                  8. Predictions & Forecasts
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {predictions.map((pred: Record<string, unknown>, idx: number) => (
                    <div key={idx} className="p-4 bg-surface-muted border border-border-color rounded-2xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-black uppercase tracking-wider text-primary-600">
                          {(pred.model_type as string) || "Forecast"}
                        </span>
                        <span className="px-2 py-0.5 bg-success-50 text-success-700 text-[10px] font-bold rounded border border-success-200">
                          {(pred.confidence as string) || "High"} Confidence
                        </span>
                      </div>
                      <p className="text-xs font-bold text-text-primary leading-relaxed">
                        {(pred.prediction as string) || (pred.model_used as string)}
                      </p>
                      <p className="text-[11px] text-text-muted">Time horizon: {(pred.time_horizon as string) || "Next period"}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-3">
              <h2 className="text-sm font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1">
                9. Executive Roadmap
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-primary-50 border border-primary-200 rounded-2xl space-y-2">
                  <span className="text-[10px] font-black uppercase tracking-wider text-primary-700">Next 30 Days</span>
                  <ul className="space-y-1.5">
                    {(roadmap.next_30_days || []).map((item: Record<string, unknown>, idx: number) => (
                      <li key={idx} className="text-[11px] text-primary-800 font-medium flex items-start gap-1.5">
                        <span className="mt-1 w-1.5 h-1.5 rounded-full bg-primary-500 flex-shrink-0"></span>
                        {(item.title as string) || "Priority action"}
                      </li>
                    ))}
                    {(roadmap.next_30_days || []).length === 0 && (
                      <li className="text-[11px] text-primary-700 font-medium">No immediate actions identified.</li>
                    )}
                  </ul>
                </div>
                <div className="p-4 bg-warning-50 border border-warning-200 rounded-2xl space-y-2">
                  <span className="text-[10px] font-black uppercase tracking-wider text-warning-700">Next 90 Days</span>
                  <ul className="space-y-1.5">
                    {(roadmap.next_90_days || []).map((item: Record<string, unknown>, idx: number) => (
                      <li key={idx} className="text-[11px] text-warning-800 font-medium flex items-start gap-1.5">
                        <span className="mt-1 w-1.5 h-1.5 rounded-full bg-warning-500 flex-shrink-0"></span>
                        {(item.title as string) || "Medium-term initiative"}
                      </li>
                    ))}
                    {(roadmap.next_90_days || []).length === 0 && (
                      <li className="text-[11px] text-warning-700 font-medium">No medium-term actions defined yet.</li>
                    )}
                  </ul>
                </div>
                <div className="p-4 bg-success-50 border border-success-200 rounded-2xl space-y-2">
                  <span className="text-[10px] font-black uppercase tracking-wider text-success-700">Next 180 Days</span>
                  <ul className="space-y-1.5">
                    {(roadmap.next_180_days || []).map((item: Record<string, unknown>, idx: number) => (
                      <li key={idx} className="text-[11px] text-success-800 font-medium flex items-start gap-1.5">
                        <span className="mt-1 w-1.5 h-1.5 rounded-full bg-success-500 flex-shrink-0"></span>
                        {(item.title as string) || "Long-term strategic goal"}
                      </li>
                    ))}
                    {(roadmap.next_180_days || []).length === 0 && (
                      <li className="text-[11px] text-success-700 font-medium">No long-term actions defined yet.</li>
                    )}
                  </ul>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h2 className="text-sm font-extrabold text-text-primary uppercase tracking-wider border-b border-border-light pb-1">
                10. Appendix
              </h2>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div className="p-3 bg-surface-muted border border-border-color rounded-xl space-y-1">
                  <span className="text-[10px] text-text-muted font-bold uppercase block">Dataset Profile</span>
                  <span className="text-text-secondary">Workspace: {wsName}</span>
                  <span className="text-text-secondary">Domain: {execSummary.domain}</span>
                  <span className="text-text-secondary">Records: {(execSummary.total_records || 0).toLocaleString()}</span>
                  <span className="text-text-secondary">Tables: {activeWs?.tables?.length || 0}</span>
                </div>
                <div className="p-3 bg-surface-muted border border-border-color rounded-xl space-y-1">
                  <span className="text-[10px] text-text-muted font-bold uppercase block">Business Intelligence Platform</span>
                  <span className="text-text-secondary">DecisionLens Enterprise Intelligence</span>
                  <span className="text-text-secondary">AI-Driven Business Analytics</span>
                  <span className="text-text-secondary">Confidence-Weighted Evidence</span>
                </div>
                <div className="p-3 bg-surface-muted border border-border-color rounded-xl space-y-1">
                  <span className="text-[10px] text-text-muted font-bold uppercase block">Model Version</span>
                  <span className="text-text-secondary">DecisionLens Enterprise Intelligence</span>
                  <span className="text-text-secondary">Semantic Analytics System</span>
                </div>
                <div className="p-3 bg-surface-muted border border-border-color rounded-xl space-y-1">
                  <span className="text-[10px] text-text-muted font-bold uppercase block">Generated</span>
                  <span className="text-text-secondary">{report?.generated_at}</span>
                  <span className="text-text-secondary">DecisionLens AI System</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
