"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorState from "@/components/ui/ErrorState";
import InsightExplanationModal, { InsightDetail } from "@/components/dashboard/InsightExplanationModal";
import {
  Zap,
  CheckCircle2,
  TrendingUp,
  HelpCircle,
  ArrowRight,
  ShieldCheck,
  Clock,
  User,
  DollarSign,
  Filter,
  RefreshCw,
  Upload,
} from "lucide-react";

interface DecisionItem {
  id: number;
  title: string;
  priority: string;
  expected_roi: string;
  confidence: string;
  risk_level: string;
  time: string;
  difficulty: string;
  owner: string;
  status: "Recommended" | "In Progress" | "Implemented" | "Deferred";
  evidence_sql: string;
  explanation: string;
  why_matters: string;
  recommended_action: string;
}

export default function ExecutiveDecisionCenterPage() {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [decisions, setDecisions] = useState<DecisionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>("All");
  const [modalOpen, setModalOpen] = useState(false);
  const [activeInsight, setActiveInsight] = useState<InsightDetail | null>(null);

  useEffect(() => {
    fetchWorkspaceAndDecisions();
    const handleWsChange = () => fetchWorkspaceAndDecisions();
    window.addEventListener("decisionlens:workspace_changed", handleWsChange);
    return () => window.removeEventListener("decisionlens:workspace_changed", handleWsChange);
  }, []);

  async function fetchWorkspaceAndDecisions() {
    try {
      setLoading(true);
      setError(null);
      const wsRes = await api.get("/workspaces");
      const wsJson = wsRes.data;
      const list = wsJson.workspaces || [];
      setWorkspaces(list);

      const storedId = typeof window !== "undefined" ? localStorage.getItem("decisionlens_active_workspace") : null;
      const currentWs =
        (storedId && list.find((w: any) => w.workspace_id === storedId)) ||
        (wsJson.active_workspace_id && list.find((w: any) => w.workspace_id === wsJson.active_workspace_id)) ||
        list.find((w: any) => w.is_active) ||
        null;

      if (currentWs) {
        const dashRes = await api.get("/dashboard/dynamic", { params: { workspace_id: currentWs.workspace_id } });
        const dashJson = dashRes.data;
        const actionItems = dashJson.action_items || [];
        const mapped: DecisionItem[] = actionItems.map((item: any, idx: number) => ({
          id: idx + 1,
          title: item.action,
          priority: item.priority || "High Priority",
          expected_roi: item.expected_roi || "Top-Line ROI",
          confidence: item.confidence || "95%",
          risk_level: "Low Risk",
          time: item.time || "14 Days",
          difficulty: item.difficulty || "Easy",
          owner: item.owner || "Executive Management",
          status: "Recommended",
          evidence_sql: item.evidence_sql || "SELECT * FROM read_parquet(...)",
          explanation: item.explanation || "Empirical insight generated from active dataset.",
          why_matters: "Direct impact on enterprise performance metrics.",
          recommended_action: `Execute action owned by ${item.owner || "Executive Team"}.`
        }));
        setDecisions(mapped);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load executive decisions. Please check your connection.";
      setError(message);
      setWorkspaces([]);
      setDecisions([]);
    } finally {
      setLoading(false);
    }
  }

  function updateStatus(id: number, newStatus: DecisionItem["status"]) {
    setDecisions((prev) =>
      prev.map((d) => (d.id === id ? { ...d, status: newStatus } : d))
    );
  }

  function openExplanation(item: DecisionItem) {
    setActiveInsight({
      title: item.title,
      why_important: item.why_matters,
      how_calculated: `analytics query: ${item.evidence_sql}`,
      recommended_action: item.recommended_action,
      business_impact: `Expected Financial ROI: ${item.expected_roi} (Risk: ${item.risk_level}, Confidence: ${item.confidence})`
    });
    setModalOpen(true);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[70vh]">
        <LoadingSpinner label="Loading executive decisions..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <ErrorState title="Failed to load executive decisions" description={error} onRetry={fetchWorkspaceAndDecisions} retryLabel="Retry" />
      </div>
    );
  }

  if (workspaces.length === 0 || decisions.length === 0) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <div className="bg-surface rounded-2xl p-12 border border-border-color shadow-lg text-center flex flex-col items-center justify-center space-y-6 max-w-xl w-full premium-card">
          <div className="p-5 bg-primary-50 text-primary-600 rounded-2xl border border-primary-100 shadow-inner">
            <Zap className="w-16 h-16 text-primary-600" />
          </div>

          <div className="space-y-2">
            <h2 className="text-3xl font-extrabold text-text-primary">No Executive Decisions Generated</h2>
            <p className="text-sm text-text-muted leading-relaxed font-medium">
              Upload a business dataset to generate automated, evidence-validated strategic decision recommendations.
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

  const filteredDecisions = decisions.filter((d) => {
    if (activeFilter === "All") return true;
    return d.status === activeFilter;
  });

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      <InsightExplanationModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        insight={activeInsight}
      />
      {/* Executive Header Banner */}
      <div className="bg-gradient-to-r from-surface via-primary-50 to-surface dark:from-background dark:via-primary-800 dark:to-background text-text-primary dark:text-white p-8 rounded-2xl border border-border-color shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-6 premium-card">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-warning-500/20 text-warning-300 text-xs font-extrabold rounded-full border border-warning-500/30 uppercase tracking-wide flex items-center gap-1">
              <Zap className="w-3.5 h-3.5 fill-amber-400" /> Executive Decision System
            </span>
          </div>

          <h1 className="text-3xl font-extrabold text-text-primary">
            Executive Decision Center
          </h1>
          <p className="text-sm text-text-muted max-w-2xl leading-relaxed">
            Prioritized strategic decisions generated from empirical workspace analysis.
          </p>
        </div>

        <div className="flex items-center gap-3 self-start md:self-auto">
          <Link
            href="/dynamic-dashboard"
            className="px-6 py-3.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-extrabold rounded-2xl transition-all shadow-lg shadow-primary-600/30 flex items-center gap-2"
          >
            <span>Back to Briefing</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Decision Center Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
          {["All", "Recommended", "In Progress", "Implemented", "Deferred"].map((filter) => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`px-4 py-2 text-xs font-extrabold rounded-xl transition-all border ${
                activeFilter === filter
                  ? "bg-primary-600 text-white border-primary-600 shadow-md shadow-primary-600/30"
                  : "bg-surface text-text-primary border-border-color hover:bg-surface-muted"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>

        <span className="text-xs font-mono text-text-muted">
          Showing {filteredDecisions.length} {filteredDecisions.length === 1 ? 'decision' : 'decisions'}
        </span>
      </div>

      <div className="space-y-4">
        {filteredDecisions.map((item) => (
          <div
            key={item.id}
            className="bg-surface rounded-2xl p-6 border border-border-color shadow-sm space-y-4 premium-card"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-light pb-4">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`px-3 py-0.5 text-[11px] font-extrabold rounded-full uppercase border ${
                      item.priority.includes("High")
                        ? "bg-error-100 text-error-800 border-error-200"
                        : "bg-warning-100 text-warning-800 border-warning-200"
                    }`}
                  >
                    {item.priority}
                  </span>

                  <span className="px-3 py-0.5 bg-success-100 text-success-800 font-extrabold text-[11px] rounded-full border border-success-200">
                    {item.confidence} Confidence
                  </span>
                </div>

                <h3 className="text-xl font-extrabold text-text-primary leading-snug">{item.title}</h3>
              </div>

              <div className="flex items-center gap-3 self-start lg:self-auto">
                <button
                  onClick={() => openExplanation(item)}
                  className="px-4 py-2 bg-surface-muted hover:bg-border-color text-text-primary text-xs font-bold rounded-xl border border-border-color flex items-center gap-1.5 transition-colors"
                >
                  <HelpCircle className="w-4 h-4 text-primary-600" />
                  <span>Explain Evidence</span>
                </button>

                <select
                  value={item.status}
                  onChange={(e) => updateStatus(item.id, e.target.value as any)}
                  className="px-3 py-2 bg-background text-text-primary text-xs font-bold rounded-xl outline-none cursor-pointer border border-border-color"
                >
                  <option value="Recommended">Status: Recommended</option>
                  <option value="In Progress">Status: In Progress</option>
                  <option value="Implemented">Status: Implemented</option>
                  <option value="Deferred">Status: Deferred</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-4 bg-surface-muted rounded-2xl border border-border-color space-y-1">
                <span className="text-text-muted font-bold uppercase text-[10px] block">Expected Financial ROI</span>
                <strong className="text-success-600 text-base font-extrabold block">{item.expected_roi}</strong>
              </div>

              <div className="p-4 bg-surface-muted rounded-2xl border border-border-color space-y-1">
                <span className="text-text-muted font-bold uppercase text-[10px] block">Time to Implement</span>
                <strong className="text-text-primary text-base font-extrabold block">{item.time}</strong>
              </div>

              <div className="p-4 bg-surface-muted rounded-2xl border border-border-color space-y-1">
                <span className="text-text-muted font-bold uppercase text-[10px] block">Implementation Owner</span>
                <strong className="text-text-primary text-base font-extrabold block">{item.owner}</strong>
              </div>
            </div>

            <div className="space-y-2 text-xs text-text-primary leading-relaxed bg-surface-muted/50 p-4 rounded-2xl border border-border-light">
              <p><strong>Business Rationale:</strong> {item.explanation}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
