"use client";

import React, { useEffect, useState, useMemo } from "react";
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
  RefreshCw,
  Plus,
  Play,
  Clock,
  User,
  X,
  FileText,
  Activity,
} from "lucide-react";
import RealtimeProgressModal from "@/components/ui/RealtimeProgressModal";
import { useProgressModal } from "@/lib/useProgressModal";

interface InvestigationItem {
  id: string;
  investigation_id?: string;
  workspace_id?: string;
  title: string;
  metric: string;
  dimension: string;
  hypothesis: string;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  status: "Active" | "In Progress" | "Resolved" | "Deferred";
  owner: string;
  created_at: string;
  updated_at?: string;
  evidence_sql?: string;
  findings?: string[];
  remediation?: string;
  notes?: string;
}

export default function InvestigationPage() {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<any>(null);
  const [investigations, setInvestigations] = useState<InvestigationItem[]>([]);
  const [selectedInv, setSelectedInv] = useState<InvestigationItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("All");

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newMetric, setNewMetric] = useState("Revenue");
  const [newDimension, setNewDimension] = useState("Category");
  const [newHypothesis, setNewHypothesis] = useState("");
  const [newPriority, setNewPriority] = useState<"CRITICAL" | "HIGH" | "MEDIUM" | "LOW">("HIGH");
  const [creating, setCreating] = useState(false);

  // Notes state
  const [noteInput, setNoteInput] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const progress = useProgressModal();

  async function loadData() {
    try {
      setLoading(true);
      setError(null);

      const wsRes = await api.get("/workspaces").catch(() => ({ data: { workspaces: [] } }));
      const wsList = wsRes.data?.workspaces || [];
      setWorkspaces(wsList);

      const storedId = typeof window !== "undefined" ? localStorage.getItem("decisionlens_active_workspace") : null;
      const found =
        (storedId && wsList.find((w: any) => w.workspace_id === storedId)) ||
        (wsRes.data?.active_workspace_id && wsList.find((w: any) => w.workspace_id === wsRes.data.active_workspace_id)) ||
        wsList.find((w: any) => w.is_active) ||
        (wsList.length > 0 ? wsList[0] : null);

      setActiveWorkspace(found);

      const targetWsId = found?.workspace_id || storedId || wsRes.data?.active_workspace_id;
      const invRes = await api.get("/investigations", { params: targetWsId ? { workspace_id: targetWsId } : {} });
      const items: InvestigationItem[] = invRes.data?.investigations || [];
      setInvestigations(items);

      if (items.length > 0) {
        setSelectedInv(items[0]);
      } else {
        setSelectedInv(null);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load investigations. Please check connection.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    const handleWsChange = () => loadData();
    window.addEventListener("decisionlens:workspace_changed", handleWsChange);
    return () => window.removeEventListener("decisionlens:workspace_changed", handleWsChange);
  }, []);

  async function handleCreateInvestigation(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;

    try {
      setCreating(true);
      const res = await api.post("/investigations", {
        title: newTitle.trim(),
        metric: newMetric.trim() || "Revenue",
        dimension: newDimension.trim() || "Category",
        hypothesis: newHypothesis.trim() || "Empirical variance detected across segments.",
        priority: newPriority,
        workspace_id: activeWorkspace?.workspace_id,
        status: "Active",
      });

      const created: InvestigationItem = res.data?.investigation;
      if (created) {
        setInvestigations((prev) => [created, ...prev]);
        setSelectedInv(created);
        setIsModalOpen(false);
        setNewTitle("");
        setNewHypothesis("");
      }
    } catch (err) {
      alert("Failed to create investigation: " + (err instanceof Error ? err.message : "Unknown error"));
    } finally {
      setCreating(false);
    }
  }

  async function handleStatusChange(newStatus: "Active" | "In Progress" | "Resolved" | "Deferred") {
    if (!selectedInv) return;
    try {
      const res = await api.patch(`/investigations/${selectedInv.id}`, {
        status: newStatus,
      }, {
        params: activeWorkspace?.workspace_id ? { workspace_id: activeWorkspace.workspace_id } : {},
      });

      const updated: InvestigationItem = res.data?.investigation || { ...selectedInv, status: newStatus };
      setSelectedInv(updated);
      setInvestigations((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err) {
      alert("Failed to update status: " + (err instanceof Error ? err.message : "Unknown error"));
    }
  }

  async function handleRunAnalysis() {
    if (!selectedInv) return;
    progress.startProgress({
      title: "Root Cause Variance Analysis",
      subtitle: `Investigating metric '${selectedInv.metric}' across '${selectedInv.dimension}'`,
      stages: [
        "Loading analytical fact and dimension tables",
        "Executing DuckDB variance decomposition",
        "Quantifying driver contributions & shifts",
        "Generating investigation evidence & findings",
      ],
      doneButtonText: "View Evidence",
    });

    try {
      setAnalyzing(true);
      progress.setProgressStage(0, 25, "Loading analytical fact and dimension tables");
      await new Promise((r) => setTimeout(r, 150));

      progress.setProgressStage(1, 55, "Executing DuckDB variance decomposition");
      const res = await api.post(`/investigations/${selectedInv.id}/analyze`, null, {
        params: activeWorkspace?.workspace_id ? { workspace_id: activeWorkspace.workspace_id } : {},
      });

      progress.setProgressStage(2, 85, "Generating investigation evidence & findings");
      const updated: InvestigationItem = res.data?.investigation || selectedInv;
      setSelectedInv(updated);
      setInvestigations((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));

      progress.completeProgress(undefined, "Root cause analysis complete!");
    } catch (err: any) {
      progress.failProgress(err.message || "Analysis execution failed.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleAddNote(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedInv || !noteInput.trim()) return;
    try {
      setSavingNote(true);
      const res = await api.patch(`/investigations/${selectedInv.id}`, {
        notes: noteInput.trim(),
      }, {
        params: activeWorkspace?.workspace_id ? { workspace_id: activeWorkspace.workspace_id } : {},
      });
      const updated: InvestigationItem = res.data?.investigation || {
        ...selectedInv,
        findings: [...(selectedInv.findings || []), `Note: ${noteInput.trim()}`],
      };
      setSelectedInv(updated);
      setInvestigations((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      setNoteInput("");
    } catch (err) {
      alert("Failed to add note: " + (err instanceof Error ? err.message : "Unknown error"));
    } finally {
      setSavingNote(false);
    }
  }

  const filteredInvestigations = useMemo(() => {
    return investigations.filter((inv) => {
      const matchesSearch =
        inv.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        inv.metric.toLowerCase().includes(searchQuery.toLowerCase()) ||
        inv.dimension.toLowerCase().includes(searchQuery.toLowerCase()) ||
        inv.hypothesis.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStatus = statusFilter === "All" || inv.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [investigations, searchQuery, statusFilter]);

  const stats = useMemo(() => {
    const total = investigations.length;
    const active = investigations.filter((i) => i.status === "Active").length;
    const inProgress = investigations.filter((i) => i.status === "In Progress").length;
    const resolved = investigations.filter((i) => i.status === "Resolved").length;
    return { total, active, inProgress, resolved };
  }, [investigations]);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <LoadingSpinner label="Loading Executive Investigation Center..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <ErrorState title="Failed to load investigations" description={error} onRetry={loadData} retryLabel="Retry" />
      </div>
    );
  }

  if (!activeWorkspace && investigations.length === 0) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <div className="bg-surface premium-card p-12 border border-border-color shadow-lg text-center flex flex-col items-center justify-center space-y-6 max-w-xl w-full">
          <div className="p-5 bg-primary-50 text-primary-600 rounded-2xl border border-primary-100 shadow-inner">
            <FolderArchive className="w-16 h-16 text-primary-600" />
          </div>
          <div className="space-y-2">
            <h2 className="text-3xl font-extrabold text-text-primary">No active business workspace</h2>
            <p className="text-sm text-text-muted leading-relaxed font-medium">
              Upload a dataset to begin empirical root cause investigations.
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

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Top Banner */}
      <div className="bg-background text-text-primary p-6 lg:p-8 rounded-2xl border border-border-color shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-6 premium-card">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-wider text-primary-600">
            <Activity className="w-4 h-4" /> Root Cause Investigation Center
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-text-primary tracking-tight">
            Executive Root Cause Investigation
          </h1>
          <p className="text-xs text-text-muted max-w-2xl leading-relaxed">
            Empirical diagnostic investigations dissecting business metric shifts, anomalies, and segment drivers for workspace:{" "}
            <span className="font-bold text-text-primary">{activeWorkspace?.name || activeWorkspace?.workspace_id || "Active Workspace"}</span>.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-5 py-3 bg-primary-600 hover:bg-primary-500 text-white font-extrabold text-xs rounded-xl transition-all shadow-lg shadow-primary-600/30 flex items-center gap-2 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Investigation</span>
          </button>
          <button
            onClick={loadData}
            className="p-3 bg-surface hover:bg-surface-muted text-text-secondary border border-border-color rounded-xl transition-all"
            title="Refresh Investigations"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-surface p-4 rounded-xl border border-border-color shadow-sm space-y-1">
          <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted">Total Investigations</span>
          <div className="text-2xl font-black text-text-primary">{stats.total}</div>
        </div>
        <div className="bg-surface p-4 rounded-xl border border-border-color shadow-sm space-y-1">
          <span className="text-[11px] font-bold uppercase tracking-wider text-warning-600">Active / Detected</span>
          <div className="text-2xl font-black text-warning-600">{stats.active}</div>
        </div>
        <div className="bg-surface p-4 rounded-xl border border-border-color shadow-sm space-y-1">
          <span className="text-[11px] font-bold uppercase tracking-wider text-primary-600">In Progress</span>
          <div className="text-2xl font-black text-primary-600">{stats.inProgress}</div>
        </div>
        <div className="bg-surface p-4 rounded-xl border border-border-color shadow-sm space-y-1">
          <span className="text-[11px] font-bold uppercase tracking-wider text-success-600">Resolved</span>
          <div className="text-2xl font-black text-success-600">{stats.resolved}</div>
        </div>
      </div>

      {/* Main Split-View Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left List Column */}
        <div className="lg:col-span-5 space-y-4">
          {/* Search & Tabs */}
          <div className="bg-surface p-4 rounded-xl border border-border-color space-y-3">
            <div className="relative">
              <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search investigations by metric, dimension, hypothesis..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-background border border-border-color rounded-xl pl-9 pr-3 py-2 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500"
              />
            </div>
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
              {(["All", "Active", "In Progress", "Resolved"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setStatusFilter(tab)}
                  className={`px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all cursor-pointer whitespace-nowrap ${
                    statusFilter === tab
                      ? "bg-primary-600 text-white shadow-sm"
                      : "bg-surface-muted text-text-muted hover:text-text-secondary"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Investigation List */}
          <div className="space-y-2 max-h-[650px] overflow-y-auto pr-1">
            {filteredInvestigations.length === 0 ? (
              <div className="bg-surface p-8 rounded-xl border border-border-color text-center space-y-2">
                <FileText className="w-8 h-8 text-text-muted mx-auto" />
                <p className="text-xs font-bold text-text-primary">No investigations match your filter</p>
                <p className="text-[11px] text-text-muted">Create a new investigation or clear search filters.</p>
              </div>
            ) : (
              filteredInvestigations.map((inv) => {
                const isSelected = selectedInv?.id === inv.id;
                const priorityColor =
                  inv.priority === "CRITICAL"
                    ? "bg-error-50 text-error-700 border-error-200"
                    : inv.priority === "HIGH"
                    ? "bg-warning-50 text-warning-700 border-warning-200"
                    : "bg-primary-50 text-primary-700 border-primary-200";

                const statusColor =
                  inv.status === "Resolved"
                    ? "bg-success-50 text-success-700 border-success-200"
                    : inv.status === "In Progress"
                    ? "bg-primary-50 text-primary-700 border-primary-200"
                    : "bg-warning-50 text-warning-700 border-warning-200";

                return (
                  <div
                    key={inv.id}
                    onClick={() => setSelectedInv(inv)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer space-y-2.5 ${
                      isSelected
                        ? "bg-primary-500/5 border-primary-500 shadow-md ring-1 ring-primary-500/20"
                        : "bg-surface hover:bg-surface-muted border-border-color"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-black border uppercase tracking-wider ${priorityColor}`}>
                          {inv.priority}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${statusColor}`}>
                          {inv.status}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-text-muted">{inv.id}</span>
                    </div>

                    <h3 className="text-xs font-bold text-text-primary line-clamp-2 leading-relaxed">
                      {inv.title}
                    </h3>

                    <div className="flex items-center justify-between text-[11px] text-text-muted pt-1 border-t border-border-light">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-text-secondary">{inv.metric}</span>
                        <span>•</span>
                        <span>by {inv.dimension}</span>
                      </div>
                      <div className="flex items-center gap-1 text-[10px]">
                        <Clock className="w-3 h-3 text-text-muted" />
                        <span>{inv.created_at ? new Date(inv.created_at).toLocaleDateString() : "Active"}</span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Detail Column */}
        <div className="lg:col-span-7">
          {selectedInv ? (
            <div className="bg-surface p-6 lg:p-8 rounded-2xl border border-border-color shadow-sm space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border-light">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-primary-600">{selectedInv.id}</span>
                    <span className="text-xs text-text-muted">•</span>
                    <span className="text-xs text-text-muted">Owner: {selectedInv.owner || "Analyst Team"}</span>
                  </div>
                  <h2 className="text-xl font-extrabold text-text-primary">{selectedInv.title}</h2>
                </div>
                {/* Status Switcher */}
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-text-muted">Status:</span>
                  <select
                    value={selectedInv.status}
                    onChange={(e) => handleStatusChange(e.target.value as any)}
                    className="bg-background border border-border-color rounded-xl px-3 py-1.5 text-xs font-bold text-text-primary focus:outline-none focus:border-primary-500"
                  >
                    <option value="Active">Active</option>
                    <option value="In Progress">In Progress</option>
                    <option value="Resolved">Resolved</option>
                    <option value="Deferred">Deferred</option>
                  </select>
                </div>
              </div>

              {/* Hypothesis Card */}
              <div className="p-4 bg-surface-muted rounded-xl border border-border-color space-y-2">
                <span className="text-[11px] font-black uppercase tracking-wider text-primary-600 block">
                  Hypothesis & Problem Statement
                </span>
                <p className="text-xs text-text-secondary leading-relaxed font-medium">
                  {selectedInv.hypothesis}
                </p>
                <div className="flex items-center gap-4 pt-1 text-[11px] text-text-muted font-medium">
                  <div>Target Metric: <strong className="text-text-primary">{selectedInv.metric}</strong></div>
                  <div>Primary Dimension: <strong className="text-text-primary">{selectedInv.dimension}</strong></div>
                  <div>Priority: <strong className="text-text-primary">{selectedInv.priority}</strong></div>
                </div>
              </div>

              {/* Empirical Drilldown Findings */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold uppercase tracking-wider text-text-primary flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-primary-500" />
                    Empirical Analysis Findings & Diagnostics
                  </span>
                  <button
                    onClick={handleRunAnalysis}
                    disabled={analyzing}
                    className="px-3.5 py-1.5 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-[11px] font-extrabold rounded-lg transition-all flex items-center gap-1.5 cursor-pointer shadow-sm"
                  >
                    <Play className={`w-3 h-3 ${analyzing ? "animate-spin" : ""}`} />
                    <span>{analyzing ? "Executing Query..." : "Execute Deep Drill-down"}</span>
                  </button>
                </div>

                <div className="space-y-2">
                  {(selectedInv.findings || []).map((finding, idx) => (
                    <div key={idx} className="p-3 bg-surface-muted border border-border-light rounded-xl flex items-start gap-2.5 text-xs text-text-secondary">
                      <CheckCircle2 className="w-4 h-4 text-success-500 flex-shrink-0 mt-0.5" />
                      <span className="leading-relaxed">{finding}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Evidence SQL */}
              {selectedInv.evidence_sql && (
                <div className="space-y-2">
                  <span className="text-xs font-extrabold uppercase tracking-wider text-text-primary flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-text-muted" />
                    DuckDB Analytical Verification Query
                  </span>
                  <pre className="p-3 bg-slate-950 text-slate-200 rounded-xl text-[11px] font-mono overflow-x-auto border border-border-color">
                    {selectedInv.evidence_sql}
                  </pre>
                </div>
              )}

              {/* Remediation & Action */}
              {selectedInv.remediation && (
                <div className="p-4 bg-success-50/20 border border-success-200 rounded-xl space-y-1.5">
                  <span className="text-[11px] font-black uppercase tracking-wider text-success-700 block">
                    Recommended Remediation Strategy
                  </span>
                  <p className="text-xs text-text-secondary leading-relaxed font-medium">
                    {selectedInv.remediation}
                  </p>
                </div>
              )}

              {/* Add Note & Findings Box */}
              <form onSubmit={handleAddNote} className="space-y-2 pt-2 border-t border-border-light">
                <span className="text-xs font-bold text-text-primary block">Add Investigation Observation Note:</span>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter analyst observation or root-cause evidence note..."
                    value={noteInput}
                    onChange={(e) => setNoteInput(e.target.value)}
                    className="flex-1 bg-background border border-border-color rounded-xl px-3 py-2 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500"
                  />
                  <button
                    type="submit"
                    disabled={savingNote || !noteInput.trim()}
                    className="px-4 py-2 bg-surface hover:bg-surface-muted disabled:opacity-50 text-text-primary border border-border-color font-bold text-xs rounded-xl transition-all"
                  >
                    {savingNote ? "Saving..." : "Add Note"}
                  </button>
                </div>
              </form>
            </div>
          ) : (
            <div className="bg-surface p-12 rounded-2xl border border-border-color text-center space-y-3">
              <Search className="w-10 h-10 text-text-muted mx-auto" />
              <h3 className="text-sm font-bold text-text-primary">Select an investigation</h3>
              <p className="text-xs text-text-muted max-w-sm mx-auto">
                Choose an empirical investigation from the left panel to inspect evidence, drivers, and remediation strategies.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* New Investigation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface border border-border-color rounded-2xl p-6 max-w-lg w-full space-y-5 shadow-2xl relative">
            <div className="flex items-center justify-between pb-3 border-b border-border-light">
              <h3 className="text-lg font-bold text-text-primary">Initiate New Investigation</h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-text-muted hover:text-text-primary rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateInvestigation} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-text-secondary">Investigation Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Investigate Q3 Revenue Decline in Retail Electronics"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full bg-background border border-border-color rounded-xl px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-primary-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text-secondary">Target Metric</label>
                  <input
                    type="text"
                    placeholder="e.g. Revenue, Cost, Churn"
                    value={newMetric}
                    onChange={(e) => setNewMetric(e.target.value)}
                    className="w-full bg-background border border-border-color rounded-xl px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-primary-500"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-text-secondary">Dimension</label>
                  <input
                    type="text"
                    placeholder="e.g. Category, Region, Channel"
                    value={newDimension}
                    onChange={(e) => setNewDimension(e.target.value)}
                    className="w-full bg-background border border-border-color rounded-xl px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-primary-500"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-text-secondary">Priority Level</label>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value as any)}
                  className="w-full bg-background border border-border-color rounded-xl px-3 py-2 text-xs font-bold text-text-primary focus:outline-none focus:border-primary-500"
                >
                  <option value="CRITICAL">CRITICAL — Severe business anomaly</option>
                  <option value="HIGH">HIGH — Material revenue/cost impact</option>
                  <option value="MEDIUM">MEDIUM — Operational optimization</option>
                  <option value="LOW">LOW — Routine data verification</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-text-secondary">Hypothesis & Problem Context</label>
                <textarea
                  rows={3}
                  placeholder="Describe the hypothesized driver (e.g. Supplier pricing change or channel shift causing margin contraction)..."
                  value={newHypothesis}
                  onChange={(e) => setNewHypothesis(e.target.value)}
                  className="w-full bg-background border border-border-color rounded-xl px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-primary-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-border-light">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-bold text-text-muted hover:text-text-primary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !newTitle.trim()}
                  className="px-5 py-2.5 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white font-extrabold text-xs rounded-xl shadow-md transition-all flex items-center gap-1.5 cursor-pointer"
                >
                  {creating ? "Creating..." : "Create Investigation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <RealtimeProgressModal
        isOpen={progress.isOpen}
        onClose={progress.closeModal}
        title={progress.title}
        subtitle={progress.subtitle}
        percentage={progress.percentage}
        currentStage={progress.currentStage}
        stages={progress.stages}
        status={progress.status}
        errorMessage={progress.errorMessage}
        stats={progress.stats}
        doneButtonText={progress.doneButtonText}
        onDone={progress.handleDone}
      />
    </div>
  );
}
