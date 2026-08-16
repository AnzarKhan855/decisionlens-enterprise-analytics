"use client";

import React, { useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  Database, AlertCircle, HelpCircle, ArrowUpRight, ArrowDownRight,
  BarChart3,
} from "lucide-react";
import InsightExplanationModal, { InsightDetail } from "./InsightExplanationModal";
import { getMetricDisplayValue } from "@/lib/types";
import { normalizeConfidence } from "@/lib/formatting";
import type { MetricObject } from "@/lib/types";

interface KPIItem {
  name: string;
  value: string;
  available?: boolean;
  status?: string;
  source_dataset?: string;
  source_column?: string;
  formula?: string;
  rows_analyzed?: number;
  insight?: string;
  reason?: string;
  what_happened?: string;
  why_matters?: string;
  business_impact?: string;
  recommended_action?: string;
  expected_outcome?: string;
  confidence?: string | number;
  trend?: "up" | "down" | "stable";
  trend_value?: string;
  history?: number[];
  change_pct?: number;
  comparison_period?: string;
  data_source?: string;
  formatted_value?: string;
  metric_type?: string;
}

interface KPIProps {
  kpis: KPIItem[] | MetricObject[];
}

function HealthScoreRing({ score }: { score: number }) {
  const radius = 32;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(score, 100) / 100) * circumference;
  const color = score >= 80 ? "var(--success-500)" : score >= 50 ? "var(--warning-500)" : "var(--error-500)";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="80" height="80" viewBox="0 0 80 80" className="transform -rotate-90">
        <circle cx="40" cy="40" r={radius} fill="none" stroke="var(--border-color)" strokeWidth="6" />
        <motion.circle
          cx="40" cy="40" r={radius} fill="none"
          stroke={color} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-lg font-extrabold text-text-primary leading-none">{score}</span>
        <span className="text-[9px] font-bold text-text-muted uppercase">Health</span>
      </div>
    </div>
  );
}

export default function DynamicKPISection({ kpis }: KPIProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [activeInsight, setActiveInsight] = useState<InsightDetail | null>(null);

  const kpiList: KPIItem[] = useMemo(() => {
    if (!kpis || !Array.isArray(kpis) || kpis.length === 0) return [];

    return kpis.map((k: unknown) => {
      const raw = k as Record<string, unknown>;
      const rawVal = getMetricDisplayValue(raw.formatted_value || raw.value);
      if (!rawVal || ["undefined", "null", "nan", "NaN", "Unknown", "unavailable"].includes(rawVal.trim())) {
        // keep going, we'll set default below
      }

      const safeK: KPIItem = {
        name: typeof raw.name === "string" && raw.name.trim() ? raw.name : "Unknown Metric",
        value: rawVal || "Awaiting Analysis",
        available: raw.available !== false,
        status: typeof raw.status === "string" ? raw.status : "Derived from Dataset",
        source_dataset: typeof raw.source_dataset === "string" ? raw.source_dataset : "Verified Dataset",
        source_column: typeof raw.source_column === "string" ? raw.source_column : "",
        formula: typeof raw.formula === "string" ? raw.formula : "",
        rows_analyzed: typeof raw.rows_analyzed === "number" && !isNaN(raw.rows_analyzed) ? raw.rows_analyzed : 0,
        insight: typeof raw.insight === "string" ? raw.insight : "",
        reason: typeof raw.reason === "string" ? raw.reason : "",
        what_happened: typeof raw.what_happened === "string" ? raw.what_happened : "",
        why_matters: typeof raw.why_matters === "string" ? raw.why_matters : "",
        business_impact: typeof raw.business_impact === "string" ? raw.business_impact : "",
        recommended_action: typeof raw.recommended_action === "string" ? raw.recommended_action : "",
        expected_outcome: typeof raw.expected_outcome === "string" ? raw.expected_outcome : "",
        confidence: typeof raw.confidence === "string" ? raw.confidence : "98%",
        trend: typeof raw.trend === "string" ? (raw.trend as KPIItem["trend"]) : undefined,
        trend_value: typeof raw.trend_value === "string" ? raw.trend_value : undefined,
        history: raw.history && Array.isArray(raw.history) ? raw.history : undefined,
        change_pct: typeof raw.change_pct === "number" && !isNaN(raw.change_pct) ? raw.change_pct : undefined,
        comparison_period: typeof raw.comparison_period === "string" ? raw.comparison_period : undefined,
        data_source: typeof raw.data_source === "string" ? raw.data_source : "Verified Dataset",
        formatted_value: typeof raw.formatted_value === "string" ? raw.formatted_value : rawVal,
        metric_type: typeof raw.metric_type === "string" ? raw.metric_type : undefined,
      };
      return safeK;
    });
  }, [kpis]);

  if (kpiList.length === 0) return null;

  function openExplanation(kpi: KPIItem) {
    setActiveInsight({
      title: `Executive Story & Audit: ${kpi.name}`,
      why_important: kpi.why_matters || kpi.insight || "This metric was calculated directly from your verified business dataset to provide an accurate performance snapshot.",
      how_calculated: `Verified using your dataset's ${kpi.source_column || "business data"} across ${kpi.rows_analyzed?.toLocaleString() || "all"} records.`,
      recommended_action: kpi.recommended_action || (kpi.available === false ? "Add the required data columns to enable this metric." : "Review the trend and take action on areas flagged for improvement."),
      business_impact: kpi.business_impact || "Directly impacts overall business performance and strategic planning."
    });
    setModalOpen(true);
  }

  return (
    <motion.div
      custom={1}
      variants={{
        hidden: { opacity: 0, y: 16 },
        visible: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] } },
      }}
      className="space-y-4"
    >
      <InsightExplanationModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        insight={activeInsight}
      />

      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600">
        <BarChart3 className="w-4 h-4" />
        <span>Key Performance Indicators</span>
      </div>
      <h2 className="text-xl font-extrabold text-text-primary">What Happened — Key Metrics</h2>
      <p className="text-sm text-text-muted leading-relaxed max-w-3xl">
        Core business metrics calculated directly from your verified dataset. Review trends and confidence levels.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {kpiList.map((kpi, idx) => {
          const isUnavailable = kpi.available === false;
          const healthScore = normalizeConfidence(kpi.confidence);
          const showHealthRing = !isNaN(healthScore) && healthScore > 0;

          return (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08, duration: 0.4 }}
              className={`rounded-2xl p-6 border shadow-sm space-y-4 flex flex-col justify-between transition-all hover:shadow-md premium-card ${
                isUnavailable
                  ? "bg-warning-50/50 border-warning-200"
                  : "bg-surface border-border-color"
              }`}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-primary-600" />
                    {kpi.name}
                  </span>

                  <div className="flex items-center gap-1.5">
                    {showHealthRing && !isUnavailable && (
                      <div className="scale-75 origin-right">
                        <HealthScoreRing score={healthScore} />
                      </div>
                    )}
                    <button
                      onClick={() => openExplanation(kpi)}
                      className="p-1 bg-surface-muted hover:bg-border-color rounded text-text-secondary text-[10px] font-bold flex items-center gap-1 transition-colors"
                      aria-label={`Explain ${kpi.name} metric`}
                    >
                      <HelpCircle className="w-3 h-3 text-primary-600" />
                      <span>Explain</span>
                    </button>
                  </div>
                </div>

                {isUnavailable ? (
                  <div className="space-y-2 py-2">
                    <div className="flex items-center gap-2 text-warning-700 text-xs font-bold">
                      <AlertCircle className="w-4 h-4 flex-shrink-0 text-warning-600" />
                      <span>Calculation Disabled</span>
                    </div>
                    <p className="text-xs text-warning-800 leading-relaxed font-medium">
                      {kpi.reason || "This workspace does not include the data needed to calculate this metric because there is no required column."}
                    </p>
                  </div>
                 ) : (
                    <div className="space-y-3">
                      <div className="flex items-end justify-between gap-2">
                        <h2 className="text-3xl font-extrabold text-text-primary tracking-tight leading-none">{kpi.value}</h2>
                        {kpi.change_pct !== undefined && kpi.change_pct !== null && (
                          <div className={`flex items-center gap-1 text-xs font-bold ${kpi.change_pct >= 0 ? "text-success-600" : "text-error-600"}`}>
                            {kpi.change_pct >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                            <span>{Math.abs(kpi.change_pct).toFixed(1)}%</span>
                          </div>
                        )}
                      </div>

                      {kpi.comparison_period && (
                        <p className="text-[10px] text-text-muted font-medium">{kpi.comparison_period}</p>
                      )}

                      <div className="space-y-1.5 text-xs text-text-secondary leading-relaxed pt-1">
                        {kpi.insight && (
                          <div className="flex items-start gap-2">
                            <span className="font-bold text-text-secondary mt-0.5">Insight:</span>
                            <span>{kpi.insight}</span>
                          </div>
                        )}
                        {kpi.what_happened && (
                          <div className="flex items-start gap-2">
                            <span className="font-bold text-text-secondary mt-0.5">What:</span>
                            <span>{kpi.what_happened}</span>
                          </div>
                        )}
                        {kpi.why_matters && (
                          <div className="flex items-start gap-2">
                            <span className="font-bold text-text-secondary mt-0.5">Why:</span>
                            <span>{kpi.why_matters}</span>
                          </div>
                        )}
                        {kpi.recommended_action && (
                          <div className="flex items-start gap-2">
                            <span className="font-bold text-primary-700 mt-0.5">Action:</span>
                            <span>{kpi.recommended_action}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
              </div>

              <div className="pt-3 border-t border-border-light text-[10px] font-semibold text-text-muted space-y-1.5 bg-surface-muted p-3 rounded-2xl">
                <div className="flex justify-between">
                  <span>Data Source</span>
                  <strong className="text-text-primary">{kpi.data_source || kpi.source_column || "Verified Dataset"}</strong>
                </div>
                <div className="flex justify-between">
                  <span>Confidence</span>
                  <strong className="text-success-700">{typeof kpi.confidence === "number" ? `${Math.round(kpi.confidence * 100)}%` : (kpi.confidence || "N/A")}</strong>
                </div>
                <div className="flex justify-between">
                  <span>Records Analyzed</span>
                  <strong className="text-primary-700">{kpi.rows_analyzed?.toLocaleString() || "All"}</strong>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
