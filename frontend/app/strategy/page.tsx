"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import api from "@/lib/api";
import {
  Target,
  AlertTriangle,
  TrendingUp,
  Zap,
  ShieldCheck,
  ArrowUpRight,
  RefreshCw,
  BarChart3,
  Lightbulb,
  CheckCircle2,
  Activity,
  Sparkles,
  Clock,
  Calendar,
  Flag,
  GitBranch,
  DollarSign,
  ArrowRightCircle,
  ArrowDownRightFromCircle,
  MinusCircle,
  Info,
  Crosshair,
  Gauge,
  LineChart,
  ArrowRight,
  BookOpen,
  Brain,
} from "lucide-react";

// ─── StrategyReport types ───────────────────────────────────────────────
interface ExecutiveSummary {
  headline: string;
  key_findings: string[];
  evidence: string[];
  business_impact: string;
  risks: string[];
  opportunities: string[];
  recommendations: string[];
  expected_outcome: string;
  confidence: number;
}

interface BusinessDriver {
  id: string;
  name: string;
  driver_type: string;
  impact_score: number;
  contribution_percentage: number;
  trend: string;
  confidence: number;
  evidence: string;
  supporting_kpis: string[];
}

interface RiskItem {
  id: string;
  title: string;
  category: string;
  probability: string;
  severity: string;
  business_impact: string;
  recommended_mitigation: string;
  confidence: number;
  affected_kpis: string[];
  evidence: string;
}

interface OpportunityItem {
  id: string;
  title: string;
  category: string;
  priority: string;
  potential_value: string;
  timeline: string;
  action: string;
  confidence: number;
  supporting_kpis: string[];
  evidence: string;
}

interface ExecutiveRecommendation {
  id: string;
  title: string;
  category: string;
  priority: string;
  reason: string;
  action: string;
  supporting_kpis: string[];
  evidence: string;
  expected_impact: string;
  estimated_roi: string;
  implementation_difficulty: string;
  timeline: string;
  confidence: number;
  risk_level: string;
  expected_gain: string;
  business_impact: string;
}

interface ScenarioAnalysis {
  scenario_name: string;
  case_type: string;
  projected_revenue: number;
  projected_profit: number | null;
  revenue_change_pct: number;
  profit_change_pct: number | null;
  risk_level: string;
  confidence: number;
  key_assumptions: string[];
  business_interpretation: string;
}

interface BusinessImpact {
  revenue_gain: number;
  revenue_loss: number;
  profit_gain: number;
  profit_loss: number;
  cost_reduction: number;
  efficiency_improvement: string;
  customer_growth: number;
  market_share_impact: string;
}

interface DecisionNode {
  id: string;
  title: string;
  description: string;
  impact: string;
  risk: string;
  roi: string;
  recommendation: string;
  children: DecisionNode[];
}

interface CrossKPIRelationship {
  source_kpi: string;
  target_kpi: string;
  relationship: string;
  explanation: string;
  confidence: number;
}

interface StrategyEvidence {
  kpi_count?: number;
  anomalies_detected?: number;
  drivers_identified?: number;
  recommendations_generated?: number;
  models_used?: string[];
  validation_status?: string;
  data_completeness?: number;
}

interface StrategyReport {
  workspace_id: string;
  domain: string;
  dataset_type: string;
  generated_at: string;
  executive_summary: ExecutiveSummary;
  business_drivers: BusinessDriver[];
  risks: RiskItem[];
  opportunities: OpportunityItem[];
  recommendations: ExecutiveRecommendation[];
  decision_tree: DecisionNode | null;
  scenario_analysis: ScenarioAnalysis[];
  business_impact: BusinessImpact;
  cross_kpi_relationships: CrossKPIRelationship[];
  confidence_score: number;
  evidence: StrategyEvidence;
  errors: string[];
}

const PRIORITY_STYLES: Record<string, { bg: string; text: string; border: string; icon: React.ReactNode }> = {
  CRITICAL: { bg: "bg-error-500/15", text: "text-error-300", border: "border-error-500/30", icon: <Flag className="w-3.5 h-3.5" /> },
  HIGH: { bg: "bg-warning-500/15", text: "text-warning-300", border: "border-warning-500/30", icon: <ArrowUpRight className="w-3.5 h-3.5" /> },
  MEDIUM: { bg: "bg-primary-500/15", text: "text-primary-300", border: "border-primary-500/30", icon: <MinusCircle className="w-3.5 h-3.5" /> },
  LOW: { bg: "bg-success-500/15", text: "text-success-300", border: "border-success-500/30", icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
};

const SEVERITY_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  CRITICAL: { bg: "bg-error-500/15", text: "text-error-300", border: "border-error-500/30" },
  HIGH: { bg: "bg-warning-500/15", text: "text-warning-300", border: "border-warning-500/30" },
  MEDIUM: { bg: "bg-primary-500/15", text: "text-primary-300", border: "border-primary-500/30" },
  LOW: { bg: "bg-success-500/15", text: "text-success-300", border: "border-success-500/30" },
};

const CASE_STYLES: Record<string, { bg: string; border: string; icon: React.ReactNode }> = {
  expected: { bg: "bg-primary-500/10", border: "border-primary-500/20", icon: <Activity className="w-4 h-4 text-primary-400" /> },
  best: { bg: "bg-success-500/10", border: "border-success-500/20", icon: <TrendingUp className="w-4 h-4 text-success-400" /> },
  worst: { bg: "bg-warning-500/10", border: "border-warning-500/20", icon: <AlertTriangle className="w-4 h-4 text-warning-400" /> },
};

function StrategyEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-4 p-8 bg-background/50 border border-border-color rounded-2xl">
      <div className="p-5 bg-primary-500/10 text-primary-400 rounded-2xl border border-primary-500/20">
        <Target className="w-10 h-10" />
      </div>
      <div>
        <h2 className="text-xl font-extrabold text-text-primary">No Strategic Analysis Available</h2>
        <p className="text-sm text-text-muted mt-2 max-w-md mx-auto">
          Strategic analysis requires an active workspace with verified numeric metrics. Upload a dataset to unlock automated strategic priorities.
        </p>
      </div>
      <Link
        href="/upload"
        className="px-5 py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-bold rounded-xl transition-all shadow-md inline-flex items-center gap-2"
      >
        <span>Upload Dataset</span>
        <ArrowUpRight className="w-4 h-4" />
      </Link>
    </div>
  );
}

function SkeletonStrategy() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-48 bg-background/80 rounded-2xl border border-border-color" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="h-64 bg-background/80 rounded-2xl border border-border-color" />
        <div className="h-64 bg-background/80 rounded-2xl border border-border-color" />
        <div className="h-64 bg-background/80 rounded-2xl border border-border-color" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="h-80 bg-background/80 rounded-2xl border border-border-color" />
        <div className="h-80 bg-background/80 rounded-2xl border border-border-color" />
      </div>
    </div>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const p = (priority || "MEDIUM").toUpperCase();
  const style = PRIORITY_STYLES[p] || PRIORITY_STYLES.MEDIUM;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 ${style.bg} ${style.text} text-[10px] font-extrabold rounded-full border ${style.border} uppercase tracking-wider`}>
      {style.icon}
      {p}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const s = (severity || "MEDIUM").toUpperCase();
  const style = SEVERITY_STYLES[s] || SEVERITY_STYLES.MEDIUM;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 ${style.bg} ${style.text} text-[10px] font-extrabold rounded-full border ${style.border} uppercase tracking-wider`}>
      {s}
    </span>
  );
}

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(confidence)));
  const color = pct >= 80 ? "bg-success-500" : pct >= 60 ? "bg-warning-500" : "bg-error-500";
  return (
    <div className="w-full">
      <div className="flex items-center justify-between text-[10px] font-semibold text-text-muted mb-1">
        <span>Confidence</span>
        <span className="text-text-secondary">{pct}%</span>
      </div>
      <div className="h-1.5 bg-background rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function TrendIcon({ trend }: { trend: string }) {
  const t = (trend || "stable").toLowerCase();
  if (t.includes("up") || t.includes("increase") || t.includes("growth"))
    return <TrendingUp className="w-3.5 h-3.5 text-success-400" />;
  if (t.includes("down") || t.includes("decrease") || t.includes("decline"))
    return <ArrowDownRightFromCircle className="w-3.5 h-3.5 text-error-400" />;
  return <MinusCircle className="w-3.5 h-3.5 text-primary-400" />;
}

function formatCurrency(val: number | undefined | null): string {
  if (val == null) return "N/A";
  const abs = Math.abs(val);
  if (abs >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `$${(val / 1_000).toFixed(1)}K`;
  return `$${val.toFixed(0)}`;
}

function formatPct(val: number | undefined | null): string {
  if (val == null) return "N/A";
  const sign = val > 0 ? "+" : "";
  return `${sign}${val.toFixed(1)}%`;
}

function DecisionTreeView({ node, depth = 0 }: { node: DecisionNode; depth?: number }) {
  if (!node) return null;
  const hasChildren = node.children && node.children.length > 0;
  return (
    <div className={`${depth > 0 ? "ml-8 border-l-2 border-border-color pl-4" : ""}`}>
      <div className="p-4 bg-background/60 rounded-2xl border border-border-color space-y-2">
        <div className="flex items-center gap-2">
          <Crosshair className="w-4 h-4 text-primary-400" />
          <h4 className="text-xs font-extrabold text-text-primary">{node.title}</h4>
        </div>
        <p className="text-xs text-text-muted leading-relaxed">{node.description}</p>
        <div className="grid grid-cols-2 gap-2 text-[10px]">
          <div className="flex items-center gap-1.5 text-text-secondary">
            <Zap className="w-3 h-3 text-warning-400" />
            <span>Impact: {node.impact}</span>
          </div>
          <div className="flex items-center gap-1.5 text-text-secondary">
            <ShieldCheck className="w-3 h-3 text-primary-400" />
            <span>Risk: {node.risk}</span>
          </div>
          <div className="flex items-center gap-1.5 text-text-secondary">
            <DollarSign className="w-3 h-3 text-success-400" />
            <span>ROI: {node.roi}</span>
          </div>
          <div className="flex items-center gap-1.5 text-text-secondary">
            <CheckCircle2 className="w-3 h-3 text-primary-400" />
            <span>Action: {node.recommendation}</span>
          </div>
        </div>
      </div>
      {hasChildren && (
        <div className="mt-3 space-y-3">
          {node.children.map((child) => (
            <DecisionTreeView key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function CrossKPIView({ relationships }: { relationships: CrossKPIRelationship[] }) {
  if (!relationships.length) return null;
  return (
     <div className="bg-background border border-border-color rounded-2xl p-6 shadow-lg space-y-4">
      <h3 className="text-xs font-bold uppercase tracking-wider text-primary-400 flex items-center gap-2">
        <GitBranch className="w-4 h-4" />
        <span>Cross-KPI Relationships</span>
      </h3>
      <div className="space-y-3">
        {relationships.map((rel, i) => (
          <div key={i} className="p-4 bg-background/60 rounded-2xl border border-border-color space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-text-primary">
              <span className="px-2 py-0.5 bg-primary-500/15 text-primary-300 rounded-lg border border-primary-500/20">{rel.source_kpi}</span>
              <ArrowRight className="w-3.5 h-3.5 text-text-muted" />
              <span className="px-2 py-0.5 bg-primary-500/15 text-primary-300 rounded-lg border border-primary-500/20">{rel.target_kpi}</span>
            </div>
            <p className="text-xs text-text-muted leading-relaxed">{rel.explanation}</p>
            <ConfidenceBar confidence={rel.confidence} />
          </div>
        ))}
      </div>
    </div>
  );
}

function EvidencePanel({ evidence }: { evidence: StrategyEvidence }) {
  if (!evidence || Object.keys(evidence).length === 0) return null;
  return (
     <div className="bg-background border border-border-color rounded-2xl p-6 shadow-lg space-y-4 premium-card">
      <h3 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-2">
        <BookOpen className="w-4 h-4 text-primary-400" />
        <span>Evidence & Model Audit</span>
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-3 bg-background/60 rounded-xl border border-border-color space-y-1">
          <div className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">KPIs Analyzed</div>
          <div className="text-lg font-extrabold text-text-primary">{evidence.kpi_count ?? "N/A"}</div>
        </div>
        <div className="p-3 bg-background/60 rounded-xl border border-border-color space-y-1">
          <div className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Anomalies</div>
          <div className="text-lg font-extrabold text-text-primary">{evidence.anomalies_detected ?? "N/A"}</div>
        </div>
        <div className="p-3 bg-background/60 rounded-xl border border-border-color space-y-1">
          <div className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Drivers</div>
          <div className="text-lg font-extrabold text-text-primary">{evidence.drivers_identified ?? "N/A"}</div>
        </div>
        <div className="p-3 bg-background/60 rounded-xl border border-border-color space-y-1">
          <div className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Recommendations</div>
          <div className="text-lg font-extrabold text-text-primary">{evidence.recommendations_generated ?? "N/A"}</div>
        </div>
      </div>
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-text-secondary">
          <Brain className="w-3.5 h-3.5 text-primary-400" />
          <span>Models Used:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {(evidence.models_used || []).map((m: string, i: number) => (
            <span key={i} className="px-2 py-1 bg-primary-500/10 text-primary-300 text-[10px] font-bold rounded-lg border border-primary-500/20">
              {m}
            </span>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <span className="text-text-muted font-semibold">Validation:</span>
        <span className={`px-2 py-1 text-[10px] font-extrabold rounded-lg border ${evidence.validation_status === "PASSED" ? "bg-success-500/15 text-success-300 border-success-500/30" : "bg-warning-500/15 text-warning-300 border-warning-500/30"}`}>
          {evidence.validation_status || "LIMITED"}
        </span>
        <span className="text-text-muted">Data Completeness: {evidence.data_completeness != null ? `${Math.round(evidence.data_completeness)}%` : "N/A"}</span>
      </div>
    </div>
  );
}

export default function StrategyPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [strategy, setStrategy] = useState<StrategyReport | null>(null);
  const [lastGenerated, setLastGenerated] = useState<string | null>(null);

  useEffect(() => {
    loadStrategy();
    const handleWsChange = () => loadStrategy();
    window.addEventListener("decisionlens:workspace_changed", handleWsChange);
    return () => window.removeEventListener("decisionlens:workspace_changed", handleWsChange);
  }, []);

  async function loadStrategy() {
    setLoading(true);
    setError(null);
    try {
      const storedId = typeof window !== "undefined" ? localStorage.getItem("decisionlens_active_workspace") : null;
      const res = await api.get("/strategy", { params: storedId ? { workspace_id: storedId } : {} });
      if (res.data) {
        setStrategy(res.data as StrategyReport);
        setLastGenerated(res.data.generated_at || new Date().toISOString());
      }
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosError = err as { response?: { status?: number; data?: { detail?: string; reason?: string } } };
        if (axiosError.response?.status === 404) {
          setStrategy(null);
          setLastGenerated(null);
        } else {
          const detail = axiosError.response?.data?.detail;
          const reason = axiosError.response?.data?.reason;
          const message = detail || reason || "Unable to load strategic analysis. Please verify your active workspace.";
          setError(message);
          setStrategy(null);
        }
      } else {
        setError("Unable to load strategic analysis. Please verify your active workspace.");
        setStrategy(null);
      }
    } finally {
      setLoading(false);
    }
  }

  const execSummary = strategy?.executive_summary;
  const recs = strategy?.recommendations || [];
  const risks = strategy?.risks || [];
  const opps = strategy?.opportunities || [];
  const drivers = strategy?.business_drivers || [];
  const scenarios = strategy?.scenario_analysis || [];
  const impact = strategy?.business_impact;
  const crossKpi = strategy?.cross_kpi_relationships || [];
  const decisionTree = strategy?.decision_tree;

  // Group recommendations by priority for Priority Actions
  const highPriorityRecs = recs.filter((r) => ["CRITICAL", "HIGH"].includes((r.priority || "").toUpperCase()));
  const mediumPriorityRecs = recs.filter((r) => (r.priority || "").toUpperCase() === "MEDIUM");
  const lowPriorityRecs = recs.filter((r) => (r.priority || "").toUpperCase() === "LOW");

  // Group recommendations by timeline for Time Horizons
  const next30 = recs.filter((r) => /30\s*days?|month|quarter/i.test(r.timeline || ""));
  const next90 = recs.filter((r) => /90\s*days?|quarter/i.test(r.timeline || ""));
  const next180 = recs.filter((r) => /180\s*days?|half\s*year|year/i.test(r.timeline || ""));

  const horizonGroups = [
    { label: "Next 30 Days", items: next30.length ? next30 : recs.slice(0, 2), icon: <Clock className="w-4 h-4" />, color: "text-error-400", border: "border-error-500/20" },
    { label: "Next 90 Days", items: next90.length ? next90 : recs.slice(2, 4), icon: <Calendar className="w-4 h-4" />, color: "text-warning-400", border: "border-warning-500/20" },
    { label: "Next 180 Days", items: next180.length ? next180 : recs.slice(4, 6), icon: <Calendar className="w-4 h-4" />, color: "text-primary-400", border: "border-primary-500/20" },
  ];

  return (
    <main className="p-6 lg:p-10 space-y-8 max-w-7xl mx-auto w-full font-sans">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border-color/80">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-400 mb-1">
            <Target className="w-4 h-4" />
            <span>Executive Strategy & Priorities</span>
          </div>
          <h1 className="text-3xl font-extrabold text-text-primary tracking-tight">
            Data-Grounded Strategic Roadmap
          </h1>
          <p className="text-sm text-text-muted mt-1">
            Evidence-backed strategic priorities, key business drivers, and operational risk mitigation derived from active workspace data.
          </p>
          {lastGenerated && !error && (
            <p className="text-[10px] text-text-muted mt-1 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Last updated: {new Date(lastGenerated).toLocaleString()}
            </p>
          )}
        </div>

        <button
          onClick={loadStrategy}
          disabled={loading}
          className="px-4 py-2 bg-background hover:bg-surface-muted border border-border-color text-text-secondary hover:text-text-primary text-xs font-bold rounded-xl transition-all flex items-center gap-2 self-start md:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-primary-400" : ""}`} />
          <span>Refresh Strategy</span>
        </button>
      </div>

      {strategy?.errors && strategy.errors.length > 0 && !error && (
        <div className="p-4 bg-warning-500/10 border border-warning-500/20 text-warning-300 rounded-2xl text-xs space-y-1">
          <div className="flex items-center gap-2 font-bold text-xs">
            <Info className="w-3.5 h-3.5 text-warning-400" />
            <span>Limited Data Mode</span>
          </div>
          {strategy.errors.map((e, i) => (
            <p key={i} className="text-text-secondary">{e}</p>
          ))}
          <p className="text-text-muted">
            Strategy generated from workspace metadata. Upload or refresh your dataset for evidence-backed recommendations.
          </p>
        </div>
      )}

      {loading ? (
        <SkeletonStrategy />
      ) : error ? (
        <div className="p-6 bg-error-500/10 border border-error-500/20 text-error-300 rounded-2xl text-xs space-y-3">
          <div className="flex items-center gap-2 font-bold text-sm">
            <AlertTriangle className="w-4 h-4 text-error-400" />
            <span>Strategy Engine Error</span>
          </div>
          <p className="text-text-secondary">{error}</p>
          <div className="flex items-center gap-3 pt-1">
            <button
              onClick={loadStrategy}
              disabled={loading}
              className="px-4 py-2 bg-error-600 hover:bg-error-500 text-white font-bold rounded-xl text-xs transition-all inline-flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Retry Strategy Loading</span>
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-background hover:bg-surface-muted border border-border-color text-text-secondary hover:text-text-primary font-bold rounded-xl text-xs transition-all"
            >
              Reload Page
            </button>
          </div>
        </div>
      ) : !strategy || (!recs.length && !execSummary?.headline) ? (
        <StrategyEmptyState />
      ) : (
        <div className="space-y-8">
          {/* ─── Executive Strategy Hero ─────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
             className="bg-gradient-to-br from-surface via-primary-50 to-surface dark:from-background dark:via-primary-800 dark:to-background border border-border-color premium-card p-8 shadow-lg space-y-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="px-3 py-1 bg-primary-500/20 text-primary-300 text-xs font-extrabold rounded-full border border-primary-500/30 uppercase tracking-wide">
                {strategy.domain || "Enterprise Domain"} Strategic Outlook
              </span>
              <div className="flex items-center gap-3">
                {strategy.confidence_score != null && (
                  <span className="px-3 py-1 bg-success-500/20 text-success-300 text-xs font-bold rounded-full border border-success-500/30 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-success-400" />
                    Confidence: {Math.round(strategy.confidence_score * 100)}%
                  </span>
                )}
                <span className="px-3 py-1 bg-background/60 text-text-secondary text-[10px] font-bold rounded-full border border-border-color uppercase tracking-wider">
                  {strategy.dataset_type || "Unknown"} Dataset
                </span>
              </div>
            </div>

            <h2 className="text-xl font-extrabold text-text-primary leading-relaxed">
              {execSummary?.headline || "Strategic roadmap constructed from empirical record distributions and statistical variance decomposition."}
            </h2>

            {execSummary?.key_findings && execSummary.key_findings.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-bold uppercase tracking-wider text-text-muted">Key Findings</div>
                <ul className="space-y-1.5">
                  {execSummary.key_findings.slice(0, 5).map((finding, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary-400 mt-0.5 shrink-0" />
                      <span>{finding}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {execSummary?.evidence && execSummary.evidence.length > 0 && (
              <div className="p-4 bg-background/40 rounded-2xl border border-border-color space-y-2">
                <div className="text-xs font-bold uppercase tracking-wider text-text-muted">Supporting Evidence</div>
                <ul className="space-y-1">
                  {execSummary.evidence.slice(0, 4).map((ev, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-text-muted">
                      <Info className="w-3 h-3 text-primary-400 mt-0.5 shrink-0" />
                      <span>{ev}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {execSummary?.business_impact && (
              <div className="flex items-center gap-2 text-xs font-semibold text-success-300">
                <DollarSign className="w-3.5 h-3.5" />
                <span>{execSummary.business_impact}</span>
              </div>
            )}

            {execSummary?.expected_outcome && (
              <div className="p-4 bg-primary-500/5 rounded-2xl border border-primary-500/15 space-y-1">
                <div className="text-xs font-bold uppercase tracking-wider text-primary-400">Expected Outcome</div>
                <p className="text-xs text-text-secondary leading-relaxed">{execSummary.expected_outcome}</p>
              </div>
            )}
          </motion.div>

          {/* ─── Top Strategic Priorities ───────────────────────────── */}
          {recs.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
              className="space-y-4"
            >
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Target className="w-4 h-4 text-primary-400" />
                <span>Top Strategic Priorities</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {recs.slice(0, 3).map((rec, i) => {
                  const title = rec.title || `Strategic Priority #${i + 1}`;
                  const evidence = rec.evidence || "Derived from statistical variance decomposition";
                  const impact = rec.expected_impact || rec.business_impact || "Positive operational impact projected";
                  const action = rec.action || rec.reason || "Execute recommended next step";
                  const confidence = rec.confidence || 75;

                      return (
                        <motion.div
                          key={rec.id || i}
                          initial={{ opacity: 0, y: 16 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.08 }}
                          className="bg-background border border-border-color hover:border-primary-500/40 rounded-2xl p-6 shadow-lg flex flex-col justify-between space-y-4 premium-card transition-all"
                        >
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-extrabold uppercase tracking-wider text-primary-400">
                                Strategic Priority #{i + 1}
                              </span>
                              <PriorityBadge priority={rec.priority} />
                            </div>

                            <h4 className="text-base font-extrabold text-text-primary leading-snug">
                              {title}
                            </h4>

                            {/* Situation */}
                            <div className="space-y-1">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted block">Situation</span>
                              <p className="text-xs text-text-secondary leading-relaxed font-medium">
                                {rec.reason || "Empirical variance detected across key business metrics."}
                              </p>
                            </div>

                            {/* Evidence */}
                            <div className="space-y-1 p-2.5 bg-background/60 rounded-xl border border-border-color">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-primary-400 block">Evidence</span>
                              <p className="text-[11px] text-text-muted leading-relaxed font-mono">
                                {evidence}
                              </p>
                            </div>

                            {/* Risk */}
                            <div className="space-y-1 p-2.5 bg-warning-500/10 rounded-xl border border-warning-500/20">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-warning-300 block">Operational Risk</span>
                              <p className="text-[11px] text-text-secondary leading-relaxed font-semibold">
                                Risk Level: {rec.risk_level || "Medium"} — {rec.business_impact || "Potential operational inefficiency if unmitigated."}
                              </p>
                            </div>
                          </div>

                          <div className="pt-3 border-t border-border-color/80 space-y-3">
                            {/* Recommendation */}
                            <div className="space-y-1">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-success-400 block">Recommendation</span>
                              <p className="text-[11px] text-text-primary font-bold leading-relaxed">
                                {action}
                              </p>
                            </div>

                            {/* Expected Impact */}
                            <div className="flex items-center justify-between text-[11px] text-success-300 font-semibold pt-1 border-t border-border-light">
                              <span>Expected Impact:</span>
                              <span className="font-extrabold">{impact}</span>
                            </div>

                            {/* Confidence */}
                            <ConfidenceBar confidence={confidence} />
                          </div>
                        </motion.div>
                      );
                })}
              </div>
            </motion.div>
          )}

          {/* ─── Priority Actions ───────────────────────────────────── */}
          {recs.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="space-y-4"
            >
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Flag className="w-4 h-4 text-primary-400" />
                <span>Priority Actions</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[
                  { label: "High", items: highPriorityRecs, color: "text-error-400", border: "border-error-500/20", bg: "bg-error-500/5" },
                  { label: "Medium", items: mediumPriorityRecs, color: "text-warning-400", border: "border-warning-500/20", bg: "bg-warning-500/5" },
                  { label: "Low", items: lowPriorityRecs.length ? lowPriorityRecs : recs.slice(3, 6), color: "text-success-400", border: "border-success-500/20", bg: "bg-success-500/5" },
                ].map((group) => (
                    <div key={group.label} className={`bg-background border ${group.border} rounded-2xl p-5 shadow-lg space-y-3 premium-card`}>
                    <h4 className={`text-xs font-extrabold uppercase tracking-wider ${group.color} flex items-center gap-2`}>
                      <Flag className="w-3.5 h-3.5" />
                      {group.label} Priority
                    </h4>
                    {group.items.length > 0 ? (
                      <div className="space-y-3">
                        {group.items.map((rec, i) => (
                          <div key={rec.id || i} className={`p-3 ${group.bg} rounded-2xl border border-border-color space-y-1.5`}>
                            <div className="text-xs font-bold text-text-primary leading-snug">{rec.title}</div>
                            <p className="text-[11px] text-text-muted leading-relaxed">{rec.reason}</p>
                            <div className="text-[10px] text-text-muted font-medium">Timeline: {rec.timeline || "TBD"}</div>
                            <ConfidenceBar confidence={rec.confidence || 75} />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-text-muted">No {group.label.toLowerCase()}-priority actions identified for this dataset.</p>
                    )}
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* ─── Time Horizons ─────────────────────────────────────── */}
          {recs.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="space-y-4"
            >
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Calendar className="w-4 h-4 text-primary-400" />
                <span>Time Horizons</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {horizonGroups.map((horizon) => (
                   <div key={horizon.label} className={`bg-background border ${horizon.border} rounded-2xl p-5 shadow-lg space-y-3 premium-card`}>
                    <h4 className={`text-xs font-extrabold uppercase tracking-wider ${horizon.color} flex items-center gap-2`}>
                      {horizon.icon}
                      {horizon.label}
                    </h4>
                    <div className="space-y-3">
                      {horizon.items.map((rec, i) => (
                        <div key={rec.id || i} className="p-3 bg-background/60 rounded-2xl border border-border-color space-y-1.5">
                           <div className="text-xs font-bold text-text-primary leading-snug">{rec.title}</div>
                          <p className="text-[11px] text-text-muted leading-relaxed">{rec.action}</p>
                          <div className="flex items-center gap-2">
                            <PriorityBadge priority={rec.priority} />
                            <span className="text-[10px] text-text-muted">{rec.implementation_difficulty || "Medium"}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* ─── Opportunities & Risks ─────────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Strategic Opportunities */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
                className="bg-background border border-border-color rounded-2xl p-6 shadow-lg space-y-4 premium-card"
             >
               <h3 className="text-xs font-bold uppercase tracking-wider text-success-400 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                <span>Key Opportunities</span>
              </h3>

              {opps.length > 0 ? (
                <div className="space-y-3">
                  {opps.slice(0, 5).map((opp, i) => (
                    <div key={opp.id || i} className="p-4 bg-background/60 rounded-2xl border border-border-color space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-xs font-extrabold text-text-primary">{opp.title || `Opportunity #${i + 1}`}</h4>
                        <div className="flex items-center gap-2">
                          <PriorityBadge priority={opp.priority} />
                          {opp.potential_value && (
                            <span className="px-2 py-0.5 bg-success-500/20 text-success-300 text-[10px] font-bold rounded-lg border border-success-500/30">
                              {opp.potential_value}
                            </span>
                          )}
                        </div>
                      </div>
                      <p className="text-xs text-text-muted leading-relaxed">{opp.evidence || opp.action || "Identified from metric segment growth analysis."}</p>
                      <div className="flex items-center gap-4 text-[10px] text-text-muted">
                        {opp.timeline && (
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {opp.timeline}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Gauge className="w-3 h-3" />
                          Confidence: {Math.round(opp.confidence || 0)}%
                        </span>
                      </div>
                      {opp.supporting_kpis && opp.supporting_kpis.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {opp.supporting_kpis.map((kpi, j) => (
                            <span key={j} className="px-2 py-0.5 bg-primary-500/10 text-primary-300 text-[10px] font-semibold rounded-lg border border-primary-500/20">
                              {kpi}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-text-muted">No explicit growth opportunities identified for this dataset profile.</p>
              )}
            </motion.div>

            {/* Strategic Risks & Mitigation */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
                className="bg-background border border-border-color rounded-2xl p-6 shadow-lg space-y-4 premium-card"
             >
               <h3 className="text-xs font-bold uppercase tracking-wider text-error-400 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                <span>Key Risks & Mitigation</span>
              </h3>

              {risks.length > 0 ? (
                <div className="space-y-3">
                  {risks.slice(0, 5).map((risk, i) => (
                    <div key={risk.id || i} className="p-4 bg-background/60 rounded-2xl border border-border-color space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-xs font-extrabold text-text-primary">{risk.title || `Risk #${i + 1}`}</h4>
                        <div className="flex items-center gap-2">
                          <SeverityBadge severity={risk.severity} />
                          {risk.probability && (
                            <span className="px-2 py-0.5 bg-warning-500/15 text-warning-300 text-[10px] font-bold rounded-lg border border-warning-500/30">
                              {risk.probability}
                            </span>
                          )}
                        </div>
                      </div>
                      <p className="text-xs text-text-muted leading-relaxed">{risk.evidence || risk.business_impact || "Concentration or variance risk identified from dataset evidence."}</p>
                      <div className="p-2.5 bg-warning-500/5 rounded-xl border border-warning-500/15 space-y-1">
                        <div className="text-[10px] font-bold text-warning-300 uppercase tracking-wider">Mitigation</div>
                        <p className="text-[11px] text-text-secondary leading-relaxed">{risk.recommended_mitigation || "Investigate and resolve."}</p>
                      </div>
                      <div className="flex items-center gap-4 text-[10px] text-text-muted">
                        {risk.affected_kpis && risk.affected_kpis.length > 0 && (
                          <span className="flex items-center gap-1">
                            <Activity className="w-3 h-3" />
                            {risk.affected_kpis.join(", ")}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Gauge className="w-3 h-3" />
                          Confidence: {Math.round(risk.confidence || 0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-text-muted">No critical concentration or operational risks detected in active workspace.</p>
              )}
            </motion.div>
          </div>

          {/* ─── Business Drivers ─────────────────────────────────── */}
          {drivers.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
               transition={{ delay: 0.3 }}
                className="bg-background border border-border-color rounded-2xl p-6 shadow-lg space-y-4 premium-card"
             >
               <h3 className="text-xs font-bold uppercase tracking-wider text-primary-400 flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                <span>Business Drivers</span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {drivers.map((driver, i) => (
                  <div key={driver.id || i} className="p-4 bg-background/60 rounded-2xl border border-border-color space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <TrendIcon trend={driver.trend} />
                        <span className="text-xs font-extrabold text-text-primary">{driver.name}</span>
                      </div>
                      <span className="text-[10px] font-semibold text-text-muted">{driver.driver_type}</span>
                    </div>
                    <div className="flex items-center gap-4 text-[11px] text-text-secondary">
                      <span>Impact: {driver.impact_score.toFixed(1)}</span>
                      <span>Contribution: {driver.contribution_percentage.toFixed(1)}%</span>
                    </div>
                    <p className="text-[11px] text-text-muted leading-relaxed">{driver.evidence}</p>
                    <ConfidenceBar confidence={driver.confidence} />
                    {driver.supporting_kpis && driver.supporting_kpis.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {driver.supporting_kpis.map((kpi, j) => (
                          <span key={j} className="px-2 py-0.5 bg-primary-500/10 text-primary-300 text-[10px] font-semibold rounded-lg border border-primary-500/20">
                            {kpi}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* ─── Decision Tree ─────────────────────────────────────── */}
          {decisionTree && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
               transition={{ delay: 0.35 }}
                className="bg-background border border-border-color rounded-2xl p-6 shadow-lg space-y-4 premium-card"
             >
               <h3 className="text-xs font-bold uppercase tracking-wider text-primary-400 flex items-center gap-2">
                <GitBranch className="w-4 h-4" />
                <span>Strategic Decision Tree</span>
              </h3>
              <DecisionTreeView node={decisionTree} />
            </motion.div>
          )}

          {/* ─── Scenario Analysis ────────────────────────────────── */}
          {scenarios.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
               transition={{ delay: 0.4 }}
                className="bg-background border border-border-color rounded-2xl p-6 shadow-lg space-y-4 premium-card"
             >
               <h3 className="text-xs font-bold uppercase tracking-wider text-primary-400 flex items-center gap-2">
                <LineChart className="w-4 h-4" />
                <span>Scenario Analysis</span>
                <span className="text-[10px] font-normal text-text-muted normal-case tracking-normal">(model-based estimates)</span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {scenarios.map((scenario, i) => {
                  const caseStyle = CASE_STYLES[scenario.case_type] || CASE_STYLES.expected;
                  return (
                    <div key={i} className={`p-5 ${caseStyle.bg} rounded-2xl border ${caseStyle.border} space-y-3`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {caseStyle.icon}
                          <h4 className="text-xs font-extrabold text-text-primary">{scenario.scenario_name}</h4>
                        </div>
                        <SeverityBadge severity={scenario.risk_level} />
                      </div>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-text-muted">Projected Revenue</span>
                            <span className="font-extrabold text-text-primary">{formatCurrency(scenario.projected_revenue)}</span>
                        </div>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-text-muted">Revenue Change</span>
                          <span className={`font-extrabold ${scenario.revenue_change_pct >= 0 ? "text-success-400" : "text-error-400"}`}>
                            {formatPct(scenario.revenue_change_pct)}
                          </span>
                        </div>
                        {scenario.projected_profit != null && (
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-text-muted">Projected Profit</span>
                              <span className="font-extrabold text-text-primary">{formatCurrency(scenario.projected_profit)}</span>
                          </div>
                        )}
                        {scenario.profit_change_pct != null && (
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-text-muted">Profit Change</span>
                            <span className={`font-extrabold ${scenario.profit_change_pct >= 0 ? "text-success-400" : "text-error-400"}`}>
                              {formatPct(scenario.profit_change_pct)}
                            </span>
                          </div>
                        )}
                      </div>
                      <ConfidenceBar confidence={scenario.confidence} />
                      {scenario.business_interpretation && (
                        <p className="text-[11px] text-text-muted leading-relaxed">{scenario.business_interpretation}</p>
                      )}
                      {scenario.key_assumptions && scenario.key_assumptions.length > 0 && (
                        <div className="space-y-1">
                          <div className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Assumptions</div>
                          <ul className="space-y-0.5">
                            {scenario.key_assumptions.map((assumption, j) => (
                              <li key={j} className="text-[10px] text-text-muted flex items-start gap-1">
                                <Info className="w-2.5 h-2.5 text-primary-400 mt-0.5 shrink-0" />
                                <span>{assumption}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}

          {/* ─── Business Impact ──────────────────────────────────── */}
          {impact && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
               transition={{ delay: 0.45 }}
                className="bg-background border border-border-color rounded-2xl p-6 shadow-lg space-y-4 premium-card"
             >
               <h3 className="text-xs font-bold uppercase tracking-wider text-primary-400 flex items-center gap-2">
                <DollarSign className="w-4 h-4" />
                <span>Estimated Business Impact</span>
                <span className="text-[10px] font-normal text-text-muted normal-case tracking-normal">(model-based estimates)</span>
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Revenue Gain", value: impact.revenue_gain, positive: true, icon: <ArrowRightCircle className="w-4 h-4 text-success-400" /> },
                  { label: "Revenue Loss", value: impact.revenue_loss, positive: false, icon: <ArrowDownRightFromCircle className="w-4 h-4 text-error-400" /> },
                  { label: "Profit Gain", value: impact.profit_gain, positive: true, icon: <TrendingUp className="w-4 h-4 text-success-400" /> },
                  { label: "Profit Loss", value: impact.profit_loss, positive: false, icon: <ArrowDownRightFromCircle className="w-4 h-4 text-error-400" /> },
                  { label: "Cost Reduction", value: impact.cost_reduction, positive: true, icon: <MinusCircle className="w-4 h-4 text-primary-400" /> },
                  { label: "Customer Growth", value: impact.customer_growth, positive: true, icon: <TrendingUp className="w-4 h-4 text-success-400" /> },
                ].map((item, i) => (
                  <div key={i} className="p-4 bg-background/60 rounded-2xl border border-border-color space-y-1">
                    <div className="flex items-center gap-2 text-text-muted">
                      {item.icon}
                      <span className="text-[10px] font-semibold uppercase tracking-wider">{item.label}</span>
                    </div>
                    <div className={`text-lg font-extrabold ${item.positive ? "text-success-400" : "text-error-400"}`}>
                      {formatCurrency(item.value)}
                    </div>
                  </div>
                ))}
              </div>
              {impact.efficiency_improvement && (
                <div className="p-3 bg-primary-500/5 rounded-xl border border-primary-500/15">
                  <span className="text-xs text-text-secondary">{impact.efficiency_improvement}</span>
                </div>
              )}
              {impact.market_share_impact && (
                <div className="p-3 bg-primary-500/5 rounded-xl border border-primary-500/15">
                  <span className="text-xs text-text-secondary">{impact.market_share_impact}</span>
                </div>
              )}
            </motion.div>
          )}

          {/* ─── Cross-KPI Relationships ──────────────────────────── */}
          {crossKpi.length > 0 && <CrossKPIView relationships={crossKpi} />}

          {/* ─── Evidence & Confidence ────────────────────────────── */}
          <EvidencePanel evidence={strategy.evidence || {}} />
        </div>
      )}
    </main>
  );
}
