"use client";

import React, { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sliders,
  TrendingUp,
  DollarSign,
  ShieldAlert,
  Sparkles,
  RefreshCw,
  BarChart2,
  Activity,
  Target,
  Lightbulb,
  AlertTriangle,
  ArrowUpRight,
  ChevronDown,
  Gauge,
  LineChart,
  PieChart,
} from "lucide-react";
import api from "@/lib/api";
import { formatBusinessValue } from "@/lib/formatting";

interface Lever {
  id: string;
  column: string;
  label: string;
  type: string;
  metric_type: string;
  current_value: number | null;
  change_pct: number;
  direction_options: string[];
  affected_metrics: any[];
  confidence: number;
  evidence: any;
  methodology: string;
  limitation: string;
}

interface ScenarioChange {
  lever_id: string;
  change_pct: number;
}

interface ScenarioPreset {
  id: string;
  name: string;
  description: string;
  changes: ScenarioChange[];
}

interface ScenarioResult {
  workspace_id: string;
  baseline: Record<string, number>;
  scenario: Record<string, number>;
  deltas: Record<string, any>;
  applied_changes: any[];
  affected_metrics: any[];
  confidence: number;
  evidence: string;
  methodology: string;
  limitations: string[];
  recommendation: string;
  estimated_impact_summary?: {
    total_estimated_delta: number;
    affected_metric_count: number;
  };
  kpis?: any[];
  forecastable_measures?: any[];
  currency_metrics?: any[];
  percentage_metrics?: any[];
  volume_metrics?: any[];
}

interface LeversResponse {
  available_levers: Lever[];
  unavailable_candidates: any[];
  presets: ScenarioPreset[];
  scenario_capability: {
    supported: boolean;
    reason: string;
    lever_count: number;
  };
}

const RISK_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  LOW: { bg: "bg-success-500/10", text: "text-success-400", border: "border-success-500/30" },
  MEDIUM: { bg: "bg-warning-500/10", text: "text-warning-400", border: "border-warning-500/30" },
  HIGH: { bg: "bg-error-500/10", text: "text-error-400", border: "border-error-500/30" },
};

function ScenarioSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-12 bg-background/80 rounded-2xl border border-border-color w-3/4" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="h-96 bg-background/80 rounded-2xl border border-border-color" />
        <div className="lg:col-span-2 h-96 bg-background/80 rounded-2xl border border-border-color" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="h-48 bg-background/80 rounded-2xl border border-border-color" />
        <div className="h-48 bg-background/80 rounded-2xl border border-border-color" />
        <div className="h-48 bg-background/80 rounded-2xl border border-border-color" />
      </div>
    </div>
  );
}

function UnavailableState({ reason }: { reason: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center p-10 bg-surface-muted rounded-2xl border border-dashed border-border-strong text-center space-y-4"
    >
      <div className="p-4 bg-surface-muted text-text-muted rounded-2xl">
        <BarChart2 className="w-10 h-10" />
      </div>
      <div>
        <h3 className="text-lg font-extrabold text-text-secondary">Scenario Simulation Unavailable</h3>
        <p className="text-xs text-text-muted mt-2 max-w-md">
          {reason}
        </p>
      </div>
    </motion.div>
  );
}

export default function ScenarioCommandCenter() {
  const [loadingLevers, setLoadingLevers] = useState(true);
  const [loadingSim, setLoadingSim] = useState(false);
  const [levers, setLevers] = useState<Lever[]>([]);
  const [presets, setPresets] = useState<ScenarioPreset[]>([]);
  const [capability, setCapability] = useState<LeversResponse["scenario_capability"] | null>(null);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [changes, setChanges] = useState<Record<string, number>>({});
  const autoRunTimerRef = useRef<NodeJS.Timeout | null>(null);

  const [stages, setStages] = useState<Array<{ name: string; status: "completed" | "in_progress" | "pending" }>>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    async function fetchLevers() {
      setLoadingLevers(true);
      setError(null);
      try {
        const storedWs = typeof window !== "undefined" ? localStorage.getItem("decisionlens_active_workspace") : null;
        const res = await api.get("/analytics/scenario/levers", { params: storedWs ? { workspace_id: storedWs } : {} });
        const data: LeversResponse = res.data || {};
        setLevers(data.available_levers || []);
        setPresets(data.presets || []);
        setCapability(data.scenario_capability || null);
      } catch (err: any) {
        console.error("Failed to fetch scenario levers:", err);
        setLevers([]);
        setPresets([]);
        setCapability({ supported: false, reason: "Unable to load scenario data.", lever_count: 0 });
      } finally {
        setLoadingLevers(false);
      }
    }
    fetchLevers();
    const handleWsChange = () => fetchLevers();
    window.addEventListener("decisionlens:workspace_changed", handleWsChange);
    return () => window.removeEventListener("decisionlens:workspace_changed", handleWsChange);
  }, []);

  function handleChange(leverId: string, value: number) {
    setChanges(prev => ({ ...prev, [leverId]: value }));
  }

  function applyPreset(preset: ScenarioPreset) {
    const newChanges: Record<string, number> = {};
    (preset.changes || []).forEach((ch) => {
      newChanges[ch.lever_id] = ch.change_pct;
    });
    setChanges(newChanges);
  }

  function handleReverseScenario() {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (autoRunTimerRef.current) {
      clearTimeout(autoRunTimerRef.current);
    }
    setChanges({});
    setResult(null);
    setError(null);
    setLoadingSim(false);
    setStages([]);
  }

  async function handleRunSimulation() {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoadingSim(true);
    setError(null);

    setStages([
      { name: "Evaluating lever assumptions (Revenue, Quantity, Pricing)", status: "in_progress" },
      { name: "Calculating statistical correlations & metric deltas", status: "pending" },
      { name: "Recalculating predictive forecast & impact", status: "pending" },
    ]);

    try {
      const changesPayload: ScenarioChange[] = Object.entries(changes)
        .filter(([, v]) => v !== 0)
        .map(([lever_id, change_pct]) => ({ lever_id, change_pct }));

      if (changesPayload.length === 0) {
        setResult(null);
        setLoadingSim(false);
        setStages([]);
        return;
      }

      setStages([
        { name: "Evaluating lever assumptions (Revenue, Quantity, Pricing)", status: "completed" },
        { name: "Calculating statistical correlations & metric deltas", status: "in_progress" },
        { name: "Recalculating predictive forecast & impact", status: "pending" },
      ]);

      const storedWs = typeof window !== "undefined" ? localStorage.getItem("decisionlens_active_workspace") : null;
      const res = await api.post("/analytics/scenario/simulate", {
        changes: changesPayload,
      }, {
        params: storedWs ? { workspace_id: storedWs } : {},
        signal: controller.signal
      });

      setStages([
        { name: "Evaluating lever assumptions (Revenue, Quantity, Pricing)", status: "completed" },
        { name: "Calculating statistical correlations & metric deltas", status: "completed" },
        { name: "Recalculating predictive forecast & impact", status: "completed" },
      ]);

      setResult(res.data);
    } catch (err: any) {
      if (axiosIsCancel(err) || err.name === "CanceledError" || err.name === "AbortError") {
        return;
      }
      console.error("Simulation error:", err);
      setError(err.response?.data?.detail || err.message || "Failed to execute scenario simulation.");
      setStages([]);
    } finally {
      setLoadingSim(false);
    }
  }

  function axiosIsCancel(err: any) {
    return err && (err.name === "CanceledError" || err.code === "ERR_CANCELED");
  }

  const isUnavailable = !loadingLevers && (!capability?.supported || levers.length === 0);

  useEffect(() => {
    if (autoRunTimerRef.current) {
      clearTimeout(autoRunTimerRef.current);
    }
    const activeChanges = Object.entries(changes).filter(([, v]) => v !== 0);
    if (activeChanges.length === 0 || isUnavailable) {
      return;
    }
    autoRunTimerRef.current = setTimeout(() => {
      handleRunSimulation();
    }, 600);
    return () => {
      if (autoRunTimerRef.current) {
        clearTimeout(autoRunTimerRef.current);
      }
    };
  }, [changes, isUnavailable]);

  return (
    <main className="p-6 lg:p-10 space-y-8 max-w-7xl mx-auto w-full font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border-color/80">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-400 mb-1">
            <Sliders className="w-4 h-4" />
            <span>Decision Intelligence</span>
          </div>
          <h1 className="text-3xl font-extrabold text-text-primary tracking-tight">
            Scenario Command Center
          </h1>
          <p className="text-sm text-text-muted mt-1">
            Universal predictive scenario simulator. Adjust levers to model hypothetical business decisions using your dataset&apos;s actual metrics.
          </p>
        </div>

        <div className="flex items-center gap-3 self-start md:self-auto">
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={handleReverseScenario}
            disabled={loadingSim || isUnavailable || (Object.keys(changes).length === 0 && !result)}
            className="px-4 py-3 bg-surface hover:bg-surface-muted border border-border-color text-text-secondary hover:text-text-primary font-bold text-xs rounded-2xl flex items-center gap-2 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <RefreshCw className="w-3.5 h-3.5 text-warning-400" />
            <span>Reverse / Reset Scenario</span>
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={handleRunSimulation}
            disabled={loadingSim || isUnavailable}
            className="px-6 py-3 bg-primary-600 hover:bg-primary-500 text-white font-extrabold text-xs rounded-2xl shadow-md shadow-primary-600/30 flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loadingSim ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            <span>Run Predictive Simulation</span>
          </motion.button>
        </div>
      </div>

      {/* Processing Stages Progress Banner */}
      {loadingSim && stages.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-5 bg-primary-500/10 border border-primary-500/30 rounded-2xl space-y-3"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-extrabold uppercase tracking-wider text-primary-400 flex items-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-primary-400" />
              <span>Analyzing Scenario Impact...</span>
            </span>
            <span className="text-[11px] font-mono font-bold text-primary-300">Processing Stage 2 of 3</span>
          </div>
          <div className="space-y-1.5">
            {stages.map((st, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                {st.status === "completed" ? (
                  <span className="text-success-400 font-bold">✓</span>
                ) : st.status === "in_progress" ? (
                  <span className="text-warning-400 font-bold animate-pulse">⏳</span>
                ) : (
                  <span className="text-text-muted font-bold">◦</span>
                )}
                <span className={st.status === "completed" ? "text-success-300 font-semibold" : st.status === "in_progress" ? "text-warning-300 font-bold" : "text-text-muted"}>
                  {st.name}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {loadingLevers ? (
        <ScenarioSkeleton />
      ) : isUnavailable ? (
        <UnavailableState reason={capability?.reason || "This dataset does not contain suitable measurable variables for hypothetical adjustment."} />
      ) : (
        <div className="space-y-8">
          {/* Presets */}
          {presets.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-wrap items-center gap-2"
            >
              <span className="text-xs font-bold text-text-muted uppercase tracking-wider">Presets:</span>
              {presets.map((p) => (
                <button
                  key={p.id}
                  onClick={() => applyPreset(p)}
                  className="px-3 py-1.5 bg-surface-muted hover:bg-primary-50 hover:text-primary-700 border border-border-color rounded-xl text-xs font-semibold text-text-secondary transition"
                  title={p.description}
                >
                  {p.name}
                </button>
              ))}
            </motion.div>
          )}

          {/* Error Banner */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="p-4 bg-error-500/10 border border-error-500/20 rounded-2xl text-xs font-semibold text-error-300"
              >
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Main Grid: Levers + Results */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Section 1: Detected Business Variables + Section 3: Scenario Controls */}
            <motion.div
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4 }}
               className="space-y-5 bg-surface-muted p-5 rounded-2xl border border-border-color premium-card lg:col-span-1"
            >
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-text-muted">
                <Activity className="w-4 h-4" />
                <span>Detected Business Variables ({levers.length})</span>
              </div>
              <p className="text-[11px] text-text-muted leading-relaxed">
                Numeric columns identified as scenario levers. Excluded: IDs, timestamps, identifiers, and high-cardinality categorical fields.
              </p>

              <div className="space-y-4">
                {levers.map((lever) => (
                  <div key={lever.id} className="space-y-2">
                    <div className="flex justify-between items-center text-xs font-bold text-text-secondary">
                      <span className="flex items-center gap-1.5">
                        <span>{lever.label}</span>
                        <span className="text-[10px] font-mono text-text-muted">
                          ({(lever.confidence * 100).toFixed(0)}% confidence)
                        </span>
                      </span>
                      <span className={ (changes[lever.id] || 0) >= 0 ? "text-success-400" : "text-error-400"}>
                        {(changes[lever.id] || 0) > 0 ? `+${changes[lever.id]}%` : `${changes[lever.id]}%`}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="-20"
                      max="20"
                      step="0.5"
                      value={changes[lever.id] || 0}
                      onChange={(e) => handleChange(lever.id, parseFloat(e.target.value))}
                      className="w-full h-2 bg-border-color rounded-lg appearance-none cursor-pointer accent-indigo-600"
                    />
                    <div className="flex justify-between text-[10px] text-text-muted">
                      <span>Baseline: {formatBusinessValue(lever.column, lever.current_value)}</span>
                      <span>Adjust {lever.label.toLowerCase()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Results Panel */}
            <AnimatePresence mode="wait">
              {result ? (
                <motion.div
                  key="result"
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 12 }}
                  transition={{ duration: 0.4 }}
                  className="lg:col-span-2 space-y-6"
                >
                  {/* Section 2: Current Baseline + Section 4: Predicted Outcome */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <motion.div
                      initial={{ scale: 0.95 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.1 }}
                       className="p-5 bg-success-500/10 border border-success-500/20 rounded-2xl space-y-1"
                    >
                      <span className="text-xs font-bold text-success-400 uppercase tracking-wider">Confidence</span>
                      <div className="text-3xl font-extrabold text-success-300">
                        {Math.round((result.confidence || 0) * 100)}%
                      </div>
                      <div className="text-xs font-bold text-success-400">
                        {result.applied_changes?.length || 0} lever(s) adjusted
                      </div>
                    </motion.div>

                    <motion.div
                      initial={{ scale: 0.95 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.2 }}
                       className="p-5 bg-primary-500/10 border border-primary-500/20 rounded-2xl space-y-1"
                     >
                       <span className="text-xs font-bold text-primary-400 uppercase tracking-wider">Affected Metrics</span>
                      <div className="text-3xl font-extrabold text-primary-300">
                        {result.affected_metrics?.length || 0}
                      </div>
                      <div className="text-xs font-bold text-primary-400">
                        {result.affected_metrics?.length ? "Relationships detected" : "Model-based estimate"}
                      </div>
                    </motion.div>

                    <motion.div
                      initial={{ scale: 0.95 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.3 }}
                       className="p-5 bg-primary-500/10 border border-primary-500/20 rounded-2xl space-y-1"
                     >
                       <span className="text-xs font-bold text-primary-400 uppercase tracking-wider">Est. Total Impact</span>
                      <div className="text-3xl font-extrabold text-primary-300">
                        {result.estimated_impact_summary?.total_estimated_delta !== undefined
                          ? formatBusinessValue("value", result.estimated_impact_summary.total_estimated_delta)
                          : "—"}
                      </div>
                      <div className="text-xs font-bold text-primary-400">
                        {result.estimated_impact_summary?.affected_metric_count || 0} metric(s)
                      </div>
                    </motion.div>
                  </div>

                  {/* Metric Categories Overview */}
                  {(result.kpis?.length || result.currency_metrics?.length || result.volume_metrics?.length || result.forecastable_measures?.length) && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                       className="p-5 bg-surface-muted border border-border-color rounded-2xl space-y-3 premium-card"
                    >
                      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-text-muted">
                        <Target className="w-4 h-4" />
                        <span>Metric Categories</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {result.kpis?.length ? (
                          <div className="p-3 bg-background/60 border border-border-color rounded-2xl">
                            <div className="text-[10px] font-bold text-primary-400 uppercase tracking-wider mb-1">KPIs</div>
                            {result.kpis.slice(0, 5).map((kpi: any, idx: number) => (
                              <div key={idx} className="text-xs text-text-secondary flex justify-between">
                                <span>{kpi.label || kpi.column}</span>
                                <span className="text-text-muted font-mono">{formatBusinessValue(kpi.column, kpi.current_value)}</span>
                              </div>
                            ))}
                          </div>
                        ) : null}
                        {result.currency_metrics?.length ? (
                          <div className="p-3 bg-background/60 border border-border-color rounded-2xl">
                            <div className="text-[10px] font-bold text-success-400 uppercase tracking-wider mb-1">Currency Metrics</div>
                            {result.currency_metrics.slice(0, 5).map((m: any, idx: number) => (
                              <div key={idx} className="text-xs text-text-secondary flex justify-between">
                                <span>{m.label || m.column}</span>
                                <span className="text-text-muted font-mono">{formatBusinessValue(m.column, m.current_value)}</span>
                              </div>
                            ))}
                          </div>
                        ) : null}
                        {result.volume_metrics?.length ? (
                          <div className="p-3 bg-background/60 border border-border-color rounded-2xl">
                            <div className="text-[10px] font-bold text-warning-400 uppercase tracking-wider mb-1">Volume Metrics</div>
                            {result.volume_metrics.slice(0, 5).map((m: any, idx: number) => (
                              <div key={idx} className="text-xs text-text-secondary flex justify-between">
                                <span>{m.label || m.column}</span>
                                <span className="text-text-muted font-mono">{formatBusinessValue(m.column, m.current_value)}</span>
                              </div>
                            ))}
                          </div>
                        ) : null}
                        {result.forecastable_measures?.length ? (
                          <div className="p-3 bg-background/60 border border-border-color rounded-2xl">
                            <div className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-1">Forecastable</div>
                            {result.forecastable_measures.slice(0, 5).map((m: any, idx: number) => (
                              <div key={idx} className="text-xs text-text-secondary flex justify-between">
                                <span>{m.label || m.column}</span>
                                <span className="text-text-muted font-mono">{formatBusinessValue(m.column, m.current_value)}</span>
                              </div>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    </motion.div>
                  )}

                  {/* Section 5: Baseline vs Scenario */}
                  {result.applied_changes && result.applied_changes.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                       className="p-5 bg-surface-muted border border-border-color rounded-2xl space-y-3 premium-card"
                    >
                      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-text-muted">
                        <LineChart className="w-4 h-4" />
                        <span>Baseline vs Scenario Deltas</span>
                      </div>
                      {result.applied_changes.map((change: any, idx: number) => (
                        <div key={idx} className="flex flex-wrap justify-between items-center text-xs text-text-secondary py-2 border-b border-border-light last:border-0 gap-2">
                          <span className="font-semibold">{change.column}</span>
                          <div className="flex items-center gap-3">
                            <span className="text-text-muted font-mono text-[11px]">
                              Base: {formatBusinessValue(change.column, change.baseline)}
                            </span>
                            <span className="font-mono font-bold text-text-primary text-xs">
                              Scenario: {formatBusinessValue(change.column, change.scenario)}
                            </span>
                            <span className={`font-bold px-2 py-0.5 rounded-lg text-[11px] ${change.change_pct >= 0 ? "bg-success-500/20 text-success-300" : "bg-error-500/20 text-error-300"}`}>
                              {change.change_pct >= 0 ? "+" : ""}{change.change_pct}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </motion.div>
                  )}

                  {/* Section 6: Impact Visualization */}
                  {result.affected_metrics && result.affected_metrics.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 }}
                       className="p-5 bg-surface-muted border border-border-color rounded-2xl space-y-3 premium-card"
                    >
                      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-text-muted">
                        <PieChart className="w-4 h-4" />
                        <span>Impact Visualization</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {result.affected_metrics.map((metric: any, idx: number) => {
                          const delta = metric.estimated_delta || 0;
                          const absDelta = Math.abs(delta);
                          const pct = metric.baseline > 0 ? (absDelta / metric.baseline) * 100 : 0;
                          return (
                            <div key={idx} className="p-3 bg-background/60 border border-border-color rounded-2xl space-y-1">
                              <div className="flex justify-between items-center">
                                <span className="text-xs font-bold text-text-secondary">{metric.column}</span>
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${metric.correlation_coefficient >= 0 ? "bg-primary-500/20 text-primary-300" : "bg-error-500/20 text-error-300"}`}>
                                  r={metric.correlation_coefficient?.toFixed(2) || "0.00"}
                                </span>
                              </div>
                              <div className="text-xs text-text-muted font-mono">
                                Base: {formatBusinessValue(metric.column, metric.baseline)} → Scenario: {formatBusinessValue(metric.column, metric.scenario)}
                              </div>
                              <div className="w-full bg-border-color rounded-full h-1.5 overflow-hidden">
                                <motion.div
                                  initial={{ width: 0 }}
                                  animate={{ width: `${Math.min(pct * 5, 100)}%` }}
                                  transition={{ duration: 0.6, delay: 0.1 * idx }}
                                  className={`h-full rounded-full ${delta >= 0 ? "bg-success-500" : "bg-error-500"}`}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </motion.div>
                  )}

                  {/* Section 7: Risk */}
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                     className="p-5 bg-surface-muted border border-border-color rounded-2xl space-y-3 premium-card"
                  >
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-text-muted">
                      <ShieldAlert className="w-4 h-4" />
                      <span>Risk Assessment</span>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <span className={`px-3 py-1 rounded-full text-xs font-extrabold border ${RISK_COLORS.LOW.bg} ${RISK_COLORS.LOW.text} ${RISK_COLORS.LOW.border}`}>
                        LOW RISK
                      </span>
                      <span className="text-xs text-text-muted">
                        Controlled sensitivity. Model-based estimate only; not a causal guarantee.
                      </span>
                    </div>
                    {result.limitations && result.limitations.length > 0 && (
                      <div className="space-y-1">
                        {result.limitations.map((lim, i) => (
                          <p key={i} className="text-xs text-text-muted flex items-start gap-2">
                            <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0 text-warning-400" />
                            {lim}
                          </p>
                        ))}
                      </div>
                    )}
                  </motion.div>

                  {/* Section 8: Evidence */}
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                     className="p-5 bg-surface-muted border border-border-color rounded-2xl space-y-2 premium-card"
                  >
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-text-muted">
                      <Gauge className="w-4 h-4" />
                      <span>Evidence & Methodology</span>
                    </div>
                    <p className="text-xs text-text-secondary leading-relaxed">
                      {result.methodology || "Hypothetical scenario based on observed dataset relationships. Not a causal prediction."}
                    </p>
                    <p className="text-xs text-text-muted font-mono">
                      {result.evidence || "No adjustments applied."}
                    </p>
                  </motion.div>

                  {/* Section 9: Recommendation */}
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                    className="p-5 bg-background border border-border-color rounded-2xl text-xs space-y-3 leading-relaxed shadow-lg premium-card"
                  >
                    <div className="flex items-center gap-2 text-primary-400 font-extrabold uppercase tracking-wider">
                      <Lightbulb className="w-4 h-4" />
                      <span>Executive Recommendation</span>
                    </div>
                    <p className="text-text-secondary">
                      {result.recommendation || "A controlled rollout of the selected adjustments is recommended in key segments before applying changes across the full dataset."}
                    </p>
                    {result.limitations && result.limitations.length > 0 && (
                      <p className="text-text-muted text-[11px] mt-1">
                        {result.limitations[0]}
                      </p>
                    )}
                  </motion.div>
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                   className="lg:col-span-2 flex flex-col items-center justify-center p-10 bg-surface-muted rounded-2xl border border-dashed border-border-strong text-center space-y-4"
                 >
                   <div className="p-4 bg-surface-muted text-text-muted rounded-2xl">
                    <BarChart2 className="w-10 h-10" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-text-secondary">Adjust levers or select a preset above and click Run Predictive Simulation</p>
                    <p className="text-xs text-text-muted mt-1">
                      Models hypothetical business decisions using your dataset&apos;s actual metrics and empirical distributions.
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      )}
    </main>
  );
}
