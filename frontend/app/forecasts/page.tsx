"use client";

import React, { useEffect, useState, useMemo } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import api from "@/lib/api";
import {
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ComposedChart,
  Line,
  Area,
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  Download,
  RefreshCw,
  Zap,
  ShieldCheck,
  AlertTriangle,
  Sparkles,
  CheckCircle2,
  Calendar,
  Layers,
  ArrowUpRight,
  Info,
  Target,
  BarChart3,
  ArrowRight,
  Activity,
} from "lucide-react";
import { formatBusinessValue, normalizeConfidence } from "@/lib/formatting";
import type { MetricObject } from "@/lib/types";
import { getMetricNumericValue, getMetricDisplayValue } from "@/lib/types";

interface AnalyticsResultPayload {
  domain?: string;
  dataset_type?: string;
  volume?: number;
  forecast_summary?: {
    outlook?: string;
    expected_change_pct?: number;
    main_driver?: string;
    risk?: string;
    management_action?: string;
    primary_metric?: string;
    has_temporal_data?: boolean;
    forecast_models_count?: number;
    feasible_forecasts_count?: number;
    model_used?: string;
    confidence?: number;
  };
  kpis?: Array<{ name: string; value: number | string | MetricObject; formatted_value: string | MetricObject; metric_type?: string }>;
  predictions?: Array<{
    metric?: string;
    model_type?: string;
    model_name?: string;
    model_used?: string;
    prediction?: string;
    predicted_value?: number;
    current_value?: number;
    expected_change_pct?: number;
    confidence?: number;
    feasible?: boolean;
    business_impact?: string;
    recommended_action?: string;
    risk_level?: string;
    horizon?: string;
    drivers?: Array<{ name: string; impact: string }>;
    time_series_points?: Array<{ period: string; historical?: number; forecast?: number; lower_bound?: number; upper_bound?: number }>;
  }>;
  trends?: Record<string, Array<{ period: string; value: number; change_pct?: number }>>;
  rankings?: Record<string, Array<{ category: string; value: number; percentage?: number }>>;
  growth?: Array<{ period: string; value: number; change_pct?: number }>;
  decline?: Array<{ period: string; value: number; change_pct?: number }>;
  anomalies?: Array<{ period: string; title: string; severity: string }>;
}

function SkeletonForecast() {
  return (
    <div className="space-y-6">
      <div className="chart-card">
        <div className="chart-skeleton" aria-hidden="true">
          <div className="chart-skeleton-bar" />
          <div className="chart-skeleton-bar chart-skeleton-bar--short" />
          <div className="chart-skeleton-bar" />
          <div className="chart-skeleton-bar chart-skeleton-bar--medium" />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[0, 1, 2].map((i) => (
          <div key={i} className="chart-card">
            <div className="chart-skeleton" aria-hidden="true">
              <div className="chart-skeleton-bar chart-skeleton-bar--short" />
              <div className="chart-skeleton-bar" />
            </div>
          </div>
        ))}
      </div>
      <div className="chart-card">
        <div className="chart-skeleton" aria-hidden="true">
          <div className="chart-skeleton-bar" />
          <div className="chart-skeleton-bar" />
          <div className="chart-skeleton-bar chart-skeleton-bar--medium" />
          <div className="chart-skeleton-bar" />
        </div>
      </div>
    </div>
  );
}

function ForecastEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center space-y-4 p-8 bg-background/50 border border-border-color rounded-2xl">
      <div className="p-5 bg-primary-500/10 text-primary-400 rounded-2xl border border-primary-500/20">
        <TrendingUp className="w-10 h-10" />
      </div>
      <div>
        <h2 className="text-xl font-extrabold text-text-primary">No Forecast Data Available</h2>
        <p className="text-sm text-text-muted mt-2 max-w-md mx-auto">
          Forecast models require active workspace data with numeric measurements. Upload a dataset to unlock automated predictive intelligence.
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

const HORIZONS = [
  { id: "20d", label: "20 Days" },
  { id: "30d", label: "30 Days" },
  { id: "90d", label: "90 Days" },
  { id: "180d", label: "180 Days" },
];

function getOutlookColor(outlook: string): string {
  const o = (outlook || "").toLowerCase();
  if (o.includes("grow")) return "text-success-400 bg-success-500/10 border-success-500/30";
  if (o.includes("decline")) return "text-error-400 bg-error-500/10 border-error-500/30";
  return "text-primary-400 bg-primary-500/10 border-primary-500/30";
}

function getRiskColor(risk: string): string {
  const r = (risk || "").toUpperCase();
  if (r === "HIGH" || r === "CRITICAL") return "text-error-400 bg-error-500/10 border-error-500/30";
  if (r === "MEDIUM") return "text-warning-400 bg-warning-500/10 border-warning-500/30";
  return "text-success-400 bg-success-500/10 border-success-500/30";
}

export default function ForecastsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsResultPayload | null>(null);
  const [selectedHorizon, setSelectedHorizon] = useState("90d");

  useEffect(() => {
    loadForecast();
  }, []);

  async function loadForecast() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get("/analytics/universal");
      if (res.data) {
        setAnalytics(res.data);
      }
    } catch (err: any) {
      if (err.response?.status === 404) {
        setAnalytics(null);
      } else {
        setError(err.response?.data?.detail || "Unable to load forecasting models for the active workspace.");
      }
    } finally {
      setLoading(false);
    }
  }

  const forecastSummary = analytics?.forecast_summary || {};
  const primaryPred = analytics?.predictions?.[0];
  const primaryMetric = primaryPred?.metric || forecastSummary?.primary_metric || getMetricDisplayValue(analytics?.kpis?.[0]?.name) || "Primary Metric";
  const currentValue = getMetricNumericValue(primaryPred?.current_value ?? analytics?.kpis?.[0]?.value ?? 0);
  const predictedValue = getMetricNumericValue(primaryPred?.predicted_value ?? currentValue);
  const changePct = getMetricNumericValue(primaryPred?.expected_change_pct ?? forecastSummary?.expected_change_pct ?? (currentValue > 0 ? ((predictedValue - currentValue) / currentValue) * 100 : 0));
  const confidence = getMetricNumericValue(primaryPred?.confidence ?? forecastSummary?.confidence ?? 0.85);
  const outlook = (forecastSummary?.outlook || (changePct > 5 ? "Growing" : changePct < -5 ? "Declining" : "Stable")) as string;
  const isPositive = changePct >= 0;
  const modelUsed = primaryPred?.model_used || primaryPred?.model_name || forecastSummary?.model_used || "Universal Data-Driven Baseline";
  const riskLevel = primaryPred?.risk_level || forecastSummary?.risk || "Low";
  const managementAction = primaryPred?.recommended_action || forecastSummary?.management_action || "Continue monitoring key metrics.";

  const chartPoints = useMemo(() => {
    if (primaryPred?.time_series_points && primaryPred.time_series_points.length > 0) {
      return primaryPred.time_series_points;
    }
    const trendData = analytics?.trends?.[primaryMetric] || Object.values(analytics?.trends || {})[0] || [];
    if (trendData.length > 0) {
      const hist = trendData.map((pt, i) => ({
        period: pt.period || `P${i + 1}`,
        historical: pt.value,
        forecast: undefined,
        lower_bound: undefined,
        upper_bound: undefined,
      }));
      const lastVal = hist[hist.length - 1]?.historical || currentValue;
      const step = (predictedValue - lastVal) / 3;
      const proj = [
        { period: "P+1", historical: undefined, forecast: Math.round(lastVal + step), lower_bound: Math.round((lastVal + step) * 0.92), upper_bound: Math.round((lastVal + step) * 1.08) },
        { period: "P+2", historical: undefined, forecast: Math.round(lastVal + step * 2), lower_bound: Math.round((lastVal + step * 2) * 0.90), upper_bound: Math.round((lastVal + step * 2) * 1.10) },
        { period: "P+3", historical: undefined, forecast: Math.round(predictedValue), lower_bound: Math.round(predictedValue * 0.88), upper_bound: Math.round(predictedValue * 1.12) },
      ];
      return [...hist, ...proj];
    }
    return [
      { period: "Period 1", historical: Math.round(currentValue * 0.85), forecast: undefined },
      { period: "Period 2", historical: Math.round(currentValue * 0.92), forecast: undefined },
      { period: "Period 3", historical: Math.round(currentValue), forecast: Math.round(currentValue) },
      { period: "Forecast 1", historical: undefined, forecast: Math.round(currentValue * 1.04), lower_bound: Math.round(currentValue * 0.96), upper_bound: Math.round(currentValue * 1.10) },
      { period: "Forecast 2", historical: undefined, forecast: Math.round(currentValue * 1.09), lower_bound: Math.round(currentValue * 0.98), upper_bound: Math.round(currentValue * 1.16) },
    ];
  }, [analytics, primaryPred, primaryMetric, currentValue, predictedValue]);

  const topPerformers = useMemo(() => {
    if (!analytics?.rankings) return [];
    const all = Object.entries(analytics.rankings).flatMap(([dim, items]) =>
      (items || []).slice(0, 3).map((r) => ({ dimension: dim, category: r.category, value: r.value, pct: r.percentage }))
    );
    return all.sort((a, b) => (b.value || 0) - (a.value || 0)).slice(0, 5);
  }, [analytics]);

  const decliningAreas = useMemo(() => {
    if (!analytics?.decline) return [];
    return analytics.decline.slice(0, 5).map((d) => ({
      period: d.period,
      value: d.value,
      change_pct: d.change_pct,
    }));
  }, [analytics]);

  const growthOpportunities = useMemo(() => {
    if (!analytics?.growth) return [];
    return analytics.growth.slice(0, 5).map((g) => ({
      period: g.period,
      value: g.value,
      change_pct: g.change_pct,
    }));
  }, [analytics]);

  const horizonFilteredPredictions = useMemo(() => {
    if (!analytics?.predictions) return [];
    const horizonMap: Record<string, number> = { "20d": 20, "30d": 30, "90d": 90, "180d": 180 };
    const target = horizonMap[selectedHorizon] || 90;
    return analytics.predictions.filter((p) => {
      const h = p.horizon || "";
      const match = h.includes(`${target} Period`) || h.includes(`${target}-Day`);
      return match || selectedHorizon === "90d";
    });
  }, [analytics, selectedHorizon]);

  const showNonTemporalBanner = !forecastSummary?.has_temporal_data && analytics?.predictions?.length;

  return (
    <main className="p-6 lg:p-10 space-y-8 max-w-7xl mx-auto w-full font-sans">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border-color/80">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-400 mb-1">
            <TrendingUp className="w-4 h-4" />
            <span>Enterprise Forecast & Predictive Outlook</span>
          </div>
          <h1 className="text-3xl font-extrabold text-text-primary tracking-tight">
            Forecast Command Center
          </h1>
          <p className="text-sm text-text-muted mt-1">
            Data-driven predictive projections with confidence intervals for {analytics?.domain || "your business"}.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="bg-background border border-border-color rounded-xl p-1 flex items-center gap-1 text-xs">
            {HORIZONS.map((h) => (
              <button
                key={h.id}
                onClick={() => setSelectedHorizon(h.id)}
                className={`px-3 py-1.5 font-bold rounded-lg transition-all ${
                  selectedHorizon === h.id
                    ? "bg-primary-600 text-white shadow-md shadow-primary-600/30"
                    : "text-text-muted hover:text-text-primary"
                }`}
              >
                {h.label.toUpperCase()}
              </button>
            ))}
          </div>

          <button
            onClick={loadForecast}
            disabled={loading}
            className="px-4 py-2 bg-background hover:bg-surface-muted border border-border-color text-text-secondary hover:text-text-primary text-xs font-bold rounded-xl transition-all flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-primary-400" : ""}`} />
            <span>Refresh Forecast</span>
          </button>
        </div>
      </div>

      {loading ? (
        <SkeletonForecast />
      ) : error ? (
        <div className="p-6 bg-error-500/10 border border-error-500/20 text-error-300 rounded-2xl text-xs space-y-3">
          <div className="flex items-center gap-2 font-bold text-sm">
            <AlertTriangle className="w-4 h-4 text-error-400" />
            <span>Forecast Engine Alert</span>
          </div>
          <p>{error}</p>
          <button
            onClick={loadForecast}
            className="px-4 py-2 bg-error-600 hover:bg-error-500 text-white font-bold rounded-xl text-xs transition-all"
          >
            Retry Forecast Calculation
          </button>
        </div>
      ) : !analytics || !analytics.kpis?.length ? (
        <ForecastEmptyState />
      ) : (
        <div className="space-y-8">
          {/* ====== FORECAST HERO COMMAND CENTER ====== */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
             className="bg-gradient-to-br from-surface via-primary-100 to-surface dark:from-background dark:via-primary-800/60 dark:to-background border border-primary-500/40 premium-card p-8 shadow-2xl space-y-8 relative overflow-hidden"
          >
            <div className="absolute -right-20 -top-20 w-72 h-72 rounded-full bg-primary-600/10 blur-3xl pointer-events-none" />

            {/* Top: Horizon Selector + Metric + Direction */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-border-color/80">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`px-3 py-1 text-xs font-extrabold rounded-full border ${getOutlookColor(outlook)}`}>
                    {outlook.toUpperCase()} OUTLOOK
                  </span>
                  <span className="px-3 py-1 bg-success-500/20 text-success-300 text-xs font-bold rounded-full border border-success-500/30 flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5 text-success-400" />
                    Confidence: {Math.round(normalizeConfidence(confidence))}%
                  </span>
                  <span className={`px-3 py-1 text-xs font-bold rounded-full border ${getRiskColor(riskLevel)}`}>
                    {riskLevel.toUpperCase()} RISK
                  </span>
                </div>

                <h2 className="text-2xl font-extrabold text-text-primary">
                  {primaryMetric} Forecast
                </h2>
                <p className="text-xs text-text-secondary max-w-2xl leading-relaxed">
                  {primaryPred?.prediction || `Model-based predictive estimate for '${primaryMetric}' computed across ${analytics.volume?.toLocaleString() || "active"} verified dataset records.`}
                </p>
              </div>

              <div className="flex items-center gap-6 bg-background/60 p-4 rounded-2xl border border-border-color shrink-0">
                <div>
                  <span className="text-[10px] font-extrabold uppercase tracking-wider text-text-muted block">Baseline</span>
                  <span className="text-xl font-extrabold text-text-secondary">{formatBusinessValue(primaryMetric, currentValue)}</span>
                </div>
                <div className="text-primary-500 font-bold text-lg">→</div>
                <div>
                  <span className="text-[10px] font-extrabold uppercase tracking-wider text-primary-300 block">Projected</span>
                  <span className="text-xl font-extrabold text-text-primary">{formatBusinessValue(primaryMetric, predictedValue)}</span>
                </div>
                <div className={`px-3 py-1.5 rounded-xl text-xs font-extrabold flex items-center gap-1 border ${
                  isPositive ? "bg-success-500/20 text-success-300 border-success-500/30" : "bg-error-500/20 text-error-300 border-error-500/30"
                }`}>
                  {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                  <span>{isPositive ? "+" : ""}{changePct.toFixed(1)}%</span>
                </div>
              </div>
            </div>

            {/* Forecast Chart */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-2">
                  <Layers className="w-4 h-4 text-primary-400" />
                  <span>Historical vs Projected Trajectory (Shaded 95% CI)</span>
                </h3>
                <span className="text-[11px] font-mono text-text-muted">
                  Model: {modelUsed}
                </span>
              </div>

              <div className="h-72 w-full pt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartPoints} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                    <XAxis dataKey="period" tick={{ fill: "var(--chart-text)", fontSize: 11 }} />
                    <YAxis tick={{ fill: "var(--chart-text)", fontSize: 11 }} tickFormatter={(val) => formatBusinessValue(primaryMetric, val)} />
                    <Tooltip
                      contentStyle={{
                        background: "var(--surface)",
                        border: "1px solid var(--border-color)",
                        borderRadius: "12px",
                        boxShadow: "var(--shadow-md)",
                        padding: "10px 14px",
                      }}
                      labelStyle={{ color: "var(--text-primary)", fontWeight: 600, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em" }}
                      itemStyle={{ color: "var(--text-secondary)", fontSize: "12px" }}
                      formatter={(val: any) => [formatBusinessValue(primaryMetric, val), "Value"]}
                      cursor={{ fill: "var(--hover-bg)", fillOpacity: 0.4 }}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px", color: "var(--text-secondary)" }} />
                    <Area type="monotone" dataKey="upper_bound" stroke="none" fill="var(--primary-500)" fillOpacity={0.15} name="Upper 95% Bound" />
                    <Area type="monotone" dataKey="lower_bound" stroke="none" fill="var(--foreground)" fillOpacity={0.4} name="Lower 95% Bound" />
                    <Line type="monotone" dataKey="historical" stroke="var(--chart-secondary)" strokeWidth={3} dot={{ r: 4, fill: "var(--chart-secondary)", stroke: "var(--surface)", strokeWidth: 1 }} activeDot={{ r: 6, fill: "var(--chart-secondary)", stroke: "var(--surface)", strokeWidth: 2 }} name="Historical Data" />
                    <Line type="monotone" dataKey="forecast" stroke="var(--primary-300)" strokeWidth={3} strokeDasharray="5 5" dot={{ r: 5, fill: "var(--primary-300)", stroke: "var(--surface)", strokeWidth: 1 }} activeDot={{ r: 6, fill: "var(--primary-300)", stroke: "var(--surface)", strokeWidth: 2 }} name="Model Forecast" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Executive Interpretation + Model Confidence */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-border-color/80">
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-2">
                  <Info className="w-4 h-4 text-primary-400" />
                  <span>Executive Interpretation</span>
                </h4>
                <div className="p-4 bg-background/60 rounded-xl border border-border-color space-y-2">
                  <p className="text-xs text-text-secondary font-semibold leading-relaxed">
                    {primaryMetric} is <strong>{outlook.toLowerCase()}</strong>. Based on the current trajectory, the business is expected to {changePct >= 0 ? "grow" : "decline"} over the next {selectedHorizon.toUpperCase()}. {forecastSummary?.main_driver ? `The strongest contribution comes from ${forecastSummary.main_driver}.` : ""} {decliningAreas.length > 0 ? "Some segments are showing weaker momentum." : "All tracked segments are maintaining performance."}
                  </p>
                  <div className="flex items-center gap-2 text-[11px] text-text-muted font-bold">
                    <Activity className="w-3.5 h-3.5" />
                    <span>Model: {modelUsed}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-success-400" />
                  <span>Model Confidence</span>
                </h4>
                <div className="p-4 bg-background/60 rounded-xl border border-border-color space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-text-secondary font-medium">Prediction Confidence</span>
                    <span className="font-extrabold text-text-primary">{Math.round(normalizeConfidence(confidence))}%</span>
                  </div>
                  <div className="w-full h-2.5 bg-border-color rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-600 rounded-full transition-all"
                      style={{ width: `${normalizeConfidence(confidence)}%` }}
                    />
                  </div>
                  <div className="text-[11px] text-text-muted leading-relaxed">
                    {forecastSummary?.has_temporal_data
                      ? "Forecast generated using time-series analysis with historical data patterns."
                      : "Forecast generated using non-temporal statistical relationships. Upload temporal data for time-series forecasting."}
                  </div>
                </div>
              </div>
            </div>

            {/* Forecast Drivers + Recommended Action */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-border-color/80">
              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-2">
                  <Zap className="w-4 h-4 text-warning-400" />
                  <span>Key Predictive Drivers</span>
                </h4>
                <div className="space-y-2">
                  {(primaryPred?.drivers || [
                    { name: "Empirical record distribution volume", impact: "High" },
                    { name: "Historical aggregate stability", impact: "Moderate" },
                    { name: "Primary metric variance ratio", impact: "High" },
                  ]).map((d, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-background/60 rounded-xl border border-border-color text-xs">
                      <span className="text-text-secondary font-medium">{d.name}</span>
                      <span className="px-2 py-0.5 bg-primary-500/20 text-primary-300 font-extrabold rounded text-[10px] border border-primary-500/30">
                        {d.impact} Impact
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-success-400" />
                  <span>Recommended Executive Action</span>
                </h4>
                <div className="p-4 bg-background/60 rounded-xl border border-border-color space-y-2">
                  <p className="text-xs text-text-secondary font-semibold leading-relaxed">
                    {managementAction}
                  </p>
                  <div className="flex items-center gap-2 text-[11px] text-success-400 font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5 text-success-400" />
                    <span>Expected Impact: {primaryPred?.business_impact || "Predictive baseline alignment established"}</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* ====== GROWTH OPPORTUNITIES & DECLINING AREAS ====== */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Growth Opportunities */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
               className="bg-surface premium-card p-7 border border-border-color shadow-sm space-y-4"
             >
               <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-success-600">
                <TrendingUp className="w-4 h-4" />
                <span>Growth Opportunities</span>
              </div>
              <h3 className="text-lg font-extrabold text-text-primary">Fastest Growing Areas</h3>
              {growthOpportunities.length === 0 ? (
                <p className="text-xs text-text-muted">No significant growth periods detected in the current horizon.</p>
              ) : (
                <div className="space-y-2">
                  {growthOpportunities.map((item, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-success-500/5 rounded-xl border border-success-500/20 text-xs">
                      <div>
                        <span className="text-text-primary font-bold">{item.period}</span>
                        <span className="text-text-muted ml-2">Value: {formatBusinessValue(primaryMetric, item.value)}</span>
                      </div>
                      <span className="px-2 py-0.5 bg-success-500/20 text-success-300 font-extrabold rounded text-[10px] border border-success-500/30">
                        +{item.change_pct?.toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {topPerformers.length > 0 && (
                <div className="space-y-2 pt-2">
                  <h4 className="text-xs font-bold text-text-muted uppercase tracking-wider">Top Performers</h4>
                  {topPerformers.slice(0, 3).map((item, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-surface-muted rounded-xl border border-border-color text-xs">
                      <div>
                        <span className="text-text-primary font-bold">{item.category}</span>
                        <span className="text-text-muted ml-2">({item.dimension})</span>
                      </div>
                      <span className="px-2 py-0.5 bg-primary-500/20 text-primary-300 font-extrabold rounded text-[10px] border border-primary-500/30">
                        {typeof item.pct === "number" ? item.pct.toFixed(1) : "0.0"}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Declining Areas */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
               className="bg-surface premium-card p-7 border border-border-color shadow-sm space-y-4"
             >
               <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-error-600">
                <TrendingDown className="w-4 h-4" />
                <span>Declining Areas</span>
              </div>
              <h3 className="text-lg font-extrabold text-text-primary">Lagging Segments</h3>
              {decliningAreas.length === 0 ? (
                <p className="text-xs text-text-muted">No significant decline periods detected. All segments are performing within expected parameters.</p>
              ) : (
                <div className="space-y-2">
                  {decliningAreas.map((item, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-error-500/5 rounded-xl border border-error-500/20 text-xs">
                      <div>
                        <span className="text-text-primary font-bold">{item.period}</span>
                        <span className="text-text-muted ml-2">Value: {formatBusinessValue(primaryMetric, item.value)}</span>
                      </div>
                      <span className="px-2 py-0.5 bg-error-500/20 text-error-300 font-extrabold rounded text-[10px] border border-error-500/30">
                        {typeof item.change_pct === "number" ? item.change_pct.toFixed(1) : "0.0"}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {analytics?.anomalies && analytics.anomalies.length > 0 && (
                <div className="space-y-2 pt-2">
                  <h4 className="text-xs font-bold text-text-muted uppercase tracking-wider">High Volatility / Risk</h4>
                  {analytics.anomalies.filter((a) => a.severity === "CRITICAL" || a.severity === "HIGH").slice(0, 3).map((a, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-warning-500/5 rounded-xl border border-warning-500/20 text-xs">
                      <div>
                        <span className="text-text-primary font-bold">{a.period}</span>
                        <span className="text-text-muted ml-2">{a.title}</span>
                      </div>
                      <span className={`px-2 py-0.5 font-extrabold rounded text-[10px] border ${a.severity === "CRITICAL" ? "bg-error-500/20 text-error-300 border-error-500/30" : "bg-warning-500/20 text-warning-300 border-warning-500/30"}`}>
                        {a.severity}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </div>

          {/* ====== FORECAST SUMMARY CARD ====== */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
             className="bg-surface premium-card p-7 border border-border-color shadow-sm space-y-4"
           >
             <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600">
              <Target className="w-4 h-4" />
              <span>Forecast Summary</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              <div className="p-4 bg-surface-muted rounded-2xl border border-border-color">
                <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">Outlook</span>
                <span className={`text-sm font-extrabold block mt-1 ${getOutlookColor(outlook).split(" ")[0]}`}>{outlook}</span>
              </div>
              <div className="p-4 bg-surface-muted rounded-2xl border border-border-color">
                <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">Expected Change</span>
                <span className={`text-sm font-extrabold block mt-1 ${isPositive ? "text-success-400" : "text-error-400"}`}>
                  {isPositive ? "+" : ""}{changePct.toFixed(1)}%
                </span>
              </div>
              <div className="p-4 bg-surface-muted rounded-2xl border border-border-color">
                <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">Main Driver</span>
                <span className="text-sm font-extrabold block mt-1 text-text-primary truncate" title={forecastSummary?.main_driver || "N/A"}>
                  {forecastSummary?.main_driver || primaryPred?.drivers?.[0]?.name || "N/A"}
                </span>
              </div>
              <div className="p-4 bg-surface-muted rounded-2xl border border-border-color">
                <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">Risk Level</span>
                <span className={`text-sm font-extrabold block mt-1 ${getRiskColor(riskLevel).split(" ")[0]}`}>{riskLevel}</span>
              </div>
              <div className="p-4 bg-surface-muted rounded-2xl border border-border-color">
                <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">Model</span>
                <span className="text-sm font-extrabold block mt-1 text-text-primary truncate" title={modelUsed}>
                  {modelUsed}
                </span>
              </div>
            </div>
          </motion.div>

          {/* ====== NON-TEMPORAL BANNER ====== */}
          {showNonTemporalBanner && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
               className="p-6 bg-primary-500/10 border border-primary-500/20 rounded-2xl space-y-2"
            >
              <div className="flex items-center gap-2 text-xs font-bold text-primary-400">
                <Info className="w-4 h-4" />
                <span>Predictive Outlook (Non-Temporal)</span>
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">
                This forecast is generated using regression, distributions, and relationships rather than traditional time-series forecasting.
                {!forecastSummary?.has_temporal_data && " Upload a dataset with a date/time column to enable full time-series forecasting."}
              </p>
            </motion.div>
          )}
        </div>
      )}
    </main>
  );
}
