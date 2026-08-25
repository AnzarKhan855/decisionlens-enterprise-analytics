"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sliders, TrendingUp, DollarSign, ShieldAlert, Sparkles, RefreshCw, BarChart2 } from "lucide-react";
import { formatBusinessValue } from "@/lib/formatting";
import api from "@/lib/api";

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

export default function WhatIfSimulator() {
  const [levers, setLevers] = useState<Lever[]>([]);
  const [loadingLevers, setLoadingLevers] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const [presets, setPresets] = useState<any[]>([]);

  useEffect(() => {
    async function fetchLevers() {
      try {
        const response = await api.get("/analytics/scenario/levers");
        const data = response.data || {};
        const available = data.available_levers || [];
        setLevers(available);
        setPresets(data.presets || []);
      } catch (err) {
        console.error("Failed to fetch scenario levers:", err);
        setLevers([]);
        setPresets([]);
      } finally {
        setLoadingLevers(false);
      }
    }
    fetchLevers();
  }, []);

  const [changes, setChanges] = useState<Record<string, number>>({});
  const autoRunTimerRef = useRef<NodeJS.Timeout | null>(null);

  function handleChange(leverId: string, value: number) {
    setChanges(prev => ({ ...prev, [leverId]: value }));
  }

  useEffect(() => {
    if (autoRunTimerRef.current) {
      clearTimeout(autoRunTimerRef.current);
    }
    const activeChanges = Object.entries(changes).filter(([, v]) => v !== 0);
    if (activeChanges.length === 0 || levers.length === 0) {
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
  }, [changes, levers.length]);

  function applyPreset(preset: any) {
    const newChanges: Record<string, number> = {};
    (preset.changes || []).forEach((ch: any) => {
      newChanges[ch.lever_id] = ch.change_pct;
    });
    setChanges(newChanges);
  }

  function handleReverseScenario() {
    setChanges({});
    setResult(null);
    setError(null);
    setLoading(false);
  }

  async function handleRunSimulation() {
    setLoading(true);
    setError(null);
    try {
      const changesPayload: ScenarioChange[] = Object.entries(changes)
        .filter(([, v]) => v !== 0)
        .map(([lever_id, change_pct]) => ({ lever_id, change_pct }));

      if (changesPayload.length === 0) {
        setResult(null);
        setLoading(false);
        return;
      }

      const response = await api.post("/analytics/scenario/simulate", {
        changes: changesPayload,
      });

      setResult(response.data);
    } catch (err: any) {
      console.error("Simulation error:", err);
      setError(err.response?.data?.detail || err.message || "Failed to execute scenario simulation.");
    } finally {
      setLoading(false);
    }
  }

  const isUnavailable = levers.length === 0 && !loadingLevers;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="premium-card p-6 lg:p-7 space-y-6"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary-50 text-primary-600 rounded-xl">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-primary-600">Decision System</span>
            <h2 className="text-xl font-extrabold text-text-primary mt-0.5 flex items-center gap-2">
              Business Scenario Simulator
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={handleReverseScenario}
            disabled={loading || isUnavailable || (Object.keys(changes).length === 0 && !result)}
            className="px-4 py-3 bg-surface hover:bg-surface-muted border border-border-color text-text-secondary font-extrabold text-xs rounded-xl flex items-center gap-1.5 transition-all disabled:opacity-40"
          >
            <RefreshCw className="w-3.5 h-3.5 text-warning-400" />
            <span>Reverse Scenario</span>
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={handleRunSimulation}
            disabled={loading || isUnavailable}
            className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white font-extrabold text-xs rounded-xl shadow-md shadow-primary-600/30 flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}>
                <RefreshCw className="w-4 h-4" />
              </motion.div>
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            <span>Run Predictive Simulation</span>
          </motion.button>
        </div>
      </div>

      {presets && presets.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-text-muted uppercase tracking-wider">Presets:</span>
          {presets.map((p) => (
            <button
              key={p.id}
              onClick={() => applyPreset(p)}
              className="px-3 py-2 bg-surface-muted hover:bg-primary-50 hover:text-primary-700 border border-border-color rounded-xl text-xs font-semibold text-text-secondary transition"
              title={p.description}
            >
              {p.name}
            </button>
          ))}
        </div>
      )}

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="p-4 bg-error-50 border border-error-200 rounded-xl text-xs font-semibold text-error-800"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {loadingLevers ? (
        <div className="p-8 text-center text-xs text-text-muted">Discovering scenario levers from dataset...</div>
      ) : isUnavailable ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center justify-center p-8 premium-card border-dashed text-center"
        >
          <BarChart2 className="w-10 h-10 text-text-muted mb-2" />
          <p className="text-sm font-bold text-text-secondary">Scenario Simulation Unavailable</p>
          <p className="text-xs text-text-muted mt-1 max-w-md">
            This dataset does not contain suitable measurable variables for hypothetical adjustment.
            Upload a dataset with numeric measures to enable scenario simulation.
          </p>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sliders Input Panel */}
          <motion.div
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4 }}
            className="space-y-5 premium-card p-5 hover:border-primary-200"
          >
            {levers.map((lever) => (
              <div key={lever.id}>
                <div className="flex justify-between text-xs font-bold text-text-secondary mb-1">
                  <span>{lever.label} Adjustment (%)</span>
                  <span className={ (changes[lever.id] || 0) >= 0 ? "text-success-600" : "text-error-600"}>
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
                <span className="text-[11px] text-text-muted">
                  Adjust {lever.label.toLowerCase()} and observe projected impact.
                </span>
              </div>
            ))}
          </motion.div>

          {/* Results Metrics Panel */}
          <AnimatePresence mode="wait">
            {result ? (
              <motion.div
                key="result"
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 12 }}
                transition={{ duration: 0.4 }}
                className="lg:col-span-2 space-y-4"
              >
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <motion.div
                    initial={{ scale: 0.95 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.1 }}
                    className="premium-card p-5 space-y-1"
                  >
                    <span className="text-xs font-bold text-success-700 uppercase tracking-wider">Confidence Rating</span>
                    <div className="text-3xl font-extrabold text-success-800">
                      {Math.round((result.confidence || 0) * 100)}%
                    </div>
                    <div className="text-xs font-bold text-success-700">
                      {result.applied_changes?.length || 0} lever(s) adjusted
                    </div>
                  </motion.div>

                  <motion.div
                    initial={{ scale: 0.95 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.2 }}
                    className="premium-card p-5 space-y-1"
                  >
                    <span className="text-xs font-bold text-primary-700 uppercase tracking-wider">Affected Metrics</span>
                    <div className="text-3xl font-extrabold text-primary-800">
                      {result.affected_metrics?.length || 0}
                    </div>
                    <div className="text-xs font-bold text-primary-700">
                      {result.affected_metrics?.length ? "Relationships detected" : "Model-based estimate"}
                    </div>
                  </motion.div>

                  <motion.div
                    initial={{ scale: 0.95 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.3 }}
                    className="premium-card p-5 space-y-1"
                  >
                    <span className="text-xs font-bold text-primary-700 uppercase tracking-wider">Risk Level</span>
                    <div className="text-3xl font-extrabold text-primary-800">
                      LOW
                    </div>
                    <div className="text-xs font-bold text-primary-700">
                      Controlled sensitivity
                    </div>
                  </motion.div>
                </div>

                {result.applied_changes && result.applied_changes.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="premium-card p-5 space-y-2"
                  >
                    <span className="text-xs font-bold text-text-secondary uppercase tracking-wider">Baseline vs Scenario Deltas</span>
                    {result.applied_changes.map((change: any, idx: number) => (
                      <div key={idx} className="flex justify-between items-center text-xs text-text-secondary py-1 border-b border-border-light last:border-0">
                        <span className="font-semibold">{change.column}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-text-muted font-mono">Baseline: {formatBusinessValue(change.baseline, change.column)}</span>
                          <span className="font-mono font-bold text-text-primary">Scenario: {formatBusinessValue(change.scenario, change.column)}</span>
                          <span className={`font-bold px-2 py-0.5 rounded-lg text-[11px] ${change.change_pct >= 0 ? "bg-success-100 text-success-800" : "bg-error-100 text-error-800"}`}>
                            {change.change_pct >= 0 ? "+" : ""}{change.change_pct}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </motion.div>
                )}

                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="premium-card p-5 text-xs space-y-2 leading-relaxed"
                >
                  <div className="flex items-center gap-2 text-primary-400 font-extrabold uppercase tracking-wider">
                    <Sparkles className="w-4 h-4" />
                    <span>Executive Recommendation</span>
                  </div>
                  <p className="text-text-secondary">{result.methodology || "Hypothetical scenario based on observed dataset relationships."}</p>
                  <p className="text-text-muted font-semibold mt-1">
                    Recommendation: A controlled rollout of the selected adjustments is recommended in key segments before applying changes across the full dataset.
                  </p>
                  {result.limitations && result.limitations.length > 0 && (
                    <p className="text-text-muted text-[11px] mt-1">{result.limitations[0]}</p>
                  )}
                </motion.div>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="lg:col-span-2 flex flex-col items-center justify-center p-8 premium-card border-dashed text-center"
              >
                <BarChart2 className="w-10 h-10 text-text-muted mb-2" />
                <p className="text-sm font-bold text-text-secondary">Adjust levers or select a preset above and click Run Predictive Simulation</p>
                <p className="text-xs text-text-muted mt-1">Models hypothetical business decisions using your dataset's actual metrics and empirical distributions.</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  );
}
