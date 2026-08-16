"use client";

import React, { useMemo } from "react";
import { motion } from "framer-motion";
import {
  BarChart3, Activity, Target, Zap,
  AlertTriangle, CheckCircle2, Download,
  HelpCircle, Database, ArrowUpRight, ArrowDownRight,
} from "lucide-react";
import {
  ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis,
} from "recharts";
import DynamicChartRenderer from "@/components/charts/DynamicChartRenderer";
import type { ChartSpec, ChartDataPoint, SectionCard, DashboardSection, KPICardItem } from "@/lib/types";

const SECTION_ICONS: Record<string, React.ElementType> = {
  kpis: BarChart3,
  health: Activity,
  trends: BarChart3,
  segment_performance: Target,
  anomalies: AlertTriangle,
  forecast: Activity,
  opportunities: CheckCircle2,
  risks: AlertTriangle,
  recommendations: Zap,
  insights: HelpCircle,
  charts: BarChart3,
  evidence: Database,
};

const SECTION_COLORS: Record<string, string> = {
  kpis: "text-primary-600",
  health: "text-success-600",
  trends: "text-primary-600",
  segment_performance: "text-warning-600",
  anomalies: "text-error-600",
  forecast: "text-primary-600",
  opportunities: "text-success-600",
  risks: "text-warning-600",
  recommendations: "text-primary-600",
  insights: "text-primary-600",
  charts: "text-primary-600",
  evidence: "text-text-muted",
};

interface Props {
  sections: DashboardSection[];
}

const KpiCardContent = React.memo(function KpiCardContent({ kpi, index }: { kpi: KPICardItem; index: number }) {
  const isUnavailable = kpi.available === false;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className={`premium-card p-6 flex flex-col justify-between transition-all hover:shadow-md space-y-4 ${
        isUnavailable ? "bg-warning-50/50 border-warning-200" : "bg-surface border-border-color"
      }`}
    >
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-extrabold uppercase tracking-wider text-text-muted flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5 text-primary-600" />
            {kpi.name}
          </span>
          <button
            className="p-1 bg-surface-muted hover:bg-border-color rounded text-text-secondary text-[10px] font-bold flex items-center gap-1 transition-colors"
            aria-label={`Explain ${kpi.name} metric`}
          >
            <HelpCircle className="w-3 h-3 text-primary-600" />
            <span>Explain</span>
          </button>
        </div>

        {isUnavailable ? (
          <div className="space-y-2 py-2">
            <div className="flex items-center gap-2 text-warning-700 text-xs font-bold">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 text-warning-600" />
              <span>Calculation Disabled</span>
            </div>
            <p className="text-xs text-warning-800 leading-relaxed font-medium">
              {kpi.insight || "This workspace does not include the data needed to calculate this metric."}
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
            </div>
          </div>
        )}
      </div>

      <div className="pt-3 border-t border-border-light text-[10px] font-semibold text-text-muted space-y-1.5 bg-surface-muted p-3 rounded-2xl">
        <div className="flex justify-between">
          <span>Data Source</span>
          <strong className="text-text-primary">{kpi.data_source || "Verified Dataset"}</strong>
        </div>
        <div className="flex justify-between">
          <span>Confidence</span>
          <strong className="text-success-700">{kpi.confidence ? `${Math.round(kpi.confidence * 100)}%` : "N/A"}</strong>
        </div>
        <div className="flex justify-between">
          <span>Records Analyzed</span>
          <strong className="text-primary-700">{(kpi.rows_analyzed != null ? kpi.rows_analyzed.toLocaleString() : "All")}</strong>
        </div>
      </div>
    </motion.div>
  );
});

const AnomalyCard = React.memo(function AnomalyCard({ card, index }: { card: SectionCard; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="p-5 bg-surface-muted rounded-2xl border border-border-color shadow-sm space-y-3"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-error-700 uppercase tracking-wider">{card.severity}</span>
        <span className="text-[10px] text-text-muted">{card.period || card.metric || ""}</span>
      </div>
      <h4 className="font-extrabold text-sm text-text-primary">{card.title}</h4>
      <p className="text-xs text-text-secondary leading-relaxed">{card.description}</p>
      <div className="grid grid-cols-2 gap-2 text-[10px]">
        <div><span className="text-text-muted">Actual:</span> <strong>{card.actual_value?.toLocaleString()}</strong></div>
        <div><span className="text-text-muted">Expected:</span> <strong>{card.expected_value?.toLocaleString()}</strong></div>
      </div>
    </motion.div>
  );
});

const SegmentPerformanceCard = React.memo(function SegmentPerformanceCard({ card, index }: { card: SectionCard; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="p-5 bg-surface-muted rounded-2xl border border-border-color shadow-sm space-y-3"
    >
      <h4 className="font-extrabold text-sm text-text-primary">{card.title}</h4>
      <p className="text-xs text-text-secondary leading-relaxed">{card.description}</p>
      {card.top_driver && (
        <div className="text-xs space-y-1">
          <span className="text-text-muted">Top Driver:</span>
          <span className="font-bold text-text-primary">{card.top_driver.category} ({card.top_driver.contribution_percentage}%)</span>
        </div>
      )}
      {card.winner && (
        <div className="text-xs">
          <span className="text-success-700 font-bold">Winner: {card.winner}</span>
          {card.difference_pct !== undefined && (
            <span className="text-text-muted ml-2">(+{Math.abs(card.difference_pct).toFixed(1)}%)</span>
          )}
        </div>
      )}
    </motion.div>
  );
});

const InsightCard = React.memo(function InsightCard({ card, index }: { card: SectionCard; index: number }) {
  const severityColors: Record<string, string> = {
    CRITICAL: "bg-error-50 border-error-200 text-error-800",
    HIGH: "bg-warning-50 border-warning-200 text-warning-800",
    LOW: "bg-success-50 border-success-200 text-success-800",
    INFO: "bg-info-50 border-info-200 text-info-800",
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className={`p-5 rounded-2xl border shadow-sm space-y-2 ${severityColors[card.severity || "INFO"] || "bg-surface-muted border-border-color"}`}
    >
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-black uppercase tracking-wider">{card.severity}</span>
        <span className="text-xs font-bold text-text-primary">{card.title}</span>
      </div>
      <p className="text-xs leading-relaxed">{card.description}</p>
    </motion.div>
  );
});

const ForecastCard = React.memo(function ForecastCard({ card, index }: { card: SectionCard; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="p-5 bg-surface-muted rounded-2xl border border-border-color shadow-sm space-y-3"
    >
      <div className="flex items-center justify-between">
        <div>
          <span className="text-[10px] font-black uppercase tracking-wider text-primary-600 block">{card.model_type || "Forecast"}</span>
          <h4 className="font-extrabold text-sm text-text-primary">{card.title || card.model_used || "Prediction"}</h4>
        </div>
        {card.confidence !== undefined && (
          <span className="px-2.5 py-1 bg-success-50 text-success-700 font-bold text-xs rounded-lg border border-success-200">{Math.round(card.confidence * 100)}% Confidence</span>
        )}
      </div>
      <p className="text-xs text-text-secondary leading-relaxed">{card.prediction || card.description}</p>
      {card.time_horizon && (
        <div className="text-xs"><span className="text-text-muted">Horizon:</span> <strong>{card.time_horizon}</strong></div>
      )}
    </motion.div>
  );
});

const OpportunityCard = React.memo(function OpportunityCard({ card, index }: { card: SectionCard; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="p-5 bg-success-50/50 rounded-2xl border border-success-200 shadow-sm space-y-3"
    >
      <div className="flex items-center justify-between">
        <h4 className="font-extrabold text-sm text-success-800">{card.title}</h4>
        <span className="px-2 py-1 bg-success-100 text-success-700 font-bold text-xs rounded-lg border border-success-200">{card.priority}</span>
      </div>
      <p className="text-xs text-success-700 leading-relaxed">{card.description}</p>
      {card.impact && <p className="text-xs text-success-600"><strong>Impact:</strong> {card.impact}</p>}
      {card.action && <p className="text-xs text-success-600"><strong>Action:</strong> {card.action}</p>}
    </motion.div>
  );
});

const RiskCard = React.memo(function RiskCard({ card, index }: { card: SectionCard; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="p-5 bg-error-50/50 rounded-2xl border border-error-200 shadow-sm space-y-3"
    >
      <div className="flex items-center justify-between">
        <h4 className="font-extrabold text-sm text-error-800">{card.title}</h4>
        <span className={`px-2 py-1 font-extrabold text-xs rounded-lg border ${card.severity === "HIGH" || card.severity === "CRITICAL" ? "bg-error-100 text-error-700 border-error-200" : "bg-warning-100 text-warning-700 border-warning-200"}`}>{card.severity}</span>
      </div>
      <p className="text-xs text-error-700 leading-relaxed">{card.description}</p>
      {card.impact && <p className="text-xs text-error-600"><strong>Impact:</strong> {card.impact}</p>}
      {card.mitigation && <p className="text-xs text-error-600"><strong>Mitigation:</strong> {card.mitigation}</p>}
    </motion.div>
  );
});

const RecommendationCard = React.memo(function RecommendationCard({ card, index }: { card: SectionCard; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="p-5 bg-primary-50/50 rounded-2xl border border-primary-200 shadow-sm space-y-3"
    >
      <div className="flex items-center justify-between">
        <h4 className="font-extrabold text-sm text-primary-800">{card.title}</h4>
        <span className="px-2 py-1 bg-primary-100 text-primary-700 font-bold text-xs rounded-lg border border-primary-200">{card.priority}</span>
      </div>
      <p className="text-xs text-primary-700 leading-relaxed">{card.reason || card.description}</p>
      {card.action && <p className="text-xs text-primary-600 font-medium"><strong>Action:</strong> {card.action}</p>}
      {card.expected_roi && <p className="text-xs text-primary-600"><strong>Expected ROI:</strong> {card.expected_roi}</p>}
    </motion.div>
  );
});

const TrendCard = React.memo(function TrendCard({ card, index }: { card: SectionCard; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="p-5 bg-surface rounded-2xl border border-border-color shadow-sm space-y-3"
    >
      <div className="flex items-center justify-between">
        <h4 className="font-extrabold text-sm text-text-primary">{card.measure?.replace(/_/g, " ").toUpperCase()}</h4>
        <span className={`text-xs font-bold ${card.direction === "up" ? "text-success-600" : card.direction === "down" ? "text-error-600" : "text-text-muted"}`}>
          {card.direction?.toUpperCase()}
        </span>
      </div>
      <div className="text-xs space-y-1">
        <div><span className="text-text-muted">Latest:</span> <strong>{card.latest_value ? card.latest_value.toLocaleString() : "0"}</strong></div>
        {card.latest_change_pct !== undefined && (() => {
          const pctStr = (card.latest_change_pct >= 0 ? "+" : "") + card.latest_change_pct.toFixed(1) + "%";
          const colorClass = card.latest_change_pct >= 0 ? "text-success-600" : "text-error-600";
          return <div><span className="text-text-muted">Change:</span> <strong className={colorClass}>{pctStr}</strong></div>;
        })()}
      </div>
      {card.chart_data && card.chart_data.length > 0 && (
        <div className="h-20 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={card.chart_data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--chart-grid)" />
              <XAxis hide />
              <YAxis hide />
              <Line type="monotone" dataKey="value" stroke={card.direction === "up" ? "var(--success-500)" : card.direction === "down" ? "var(--error-500)" : "var(--primary-500)"} strokeWidth={2} dot={false} activeDot={{ r: 4, fill: "var(--primary-500)", stroke: "var(--surface)", strokeWidth: 2 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </motion.div>
  );
});

const DefaultCard = React.memo(function DefaultCard({ card, index }: { card: SectionCard; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className="p-5 bg-surface rounded-2xl border border-border-color shadow-sm space-y-2"
    >
      <h4 className="font-extrabold text-sm text-text-primary">{card.title || card.id}</h4>
      {card.description && <p className="text-xs text-text-secondary leading-relaxed">{card.description}</p>}
    </motion.div>
  );
});

function renderCardContent(card: SectionCard, sectionId: string, index: number) {
  switch (sectionId) {
    case "kpis": {
      const kpi: KPICardItem = {
        name: card.name || "Unknown Metric",
        value: card.formatted_value || String(card.latest_value ?? card.value ?? "N/A"),
        formatted_value: card.formatted_value || String(card.latest_value ?? card.value ?? "N/A"),
        metric_type: card.metric_type || "",
        source_column: card.source_column || "",
        formula: card.formula || "",
        rows_analyzed: card.data_points ?? card.rows_analyzed ?? 0,
        confidence: typeof card.latest_value === "number" ? 0.95 : 0.9,
        available: true,
        status: card.status || "Derived from Dataset",
        insight: card.description || "",
        trend_value: card.trend || "stable",
        change_pct: card.latest_change_pct,
        comparison_period: "",
        data_source: card.source_column || "Verified Dataset",
      };
      return <KpiCardContent key={card.id || index} kpi={kpi} index={index} />;
    }
    case "anomalies":
      return <AnomalyCard key={card.id || index} card={card} index={index} />;
    case "segment_performance":
      return <SegmentPerformanceCard key={card.id || index} card={card} index={index} />;
    case "insights":
      return <InsightCard key={card.id || index} card={card} index={index} />;
    case "forecast":
    case "predictions":
      return <ForecastCard key={card.id || index} card={card} index={index} />;
    case "opportunities":
      return <OpportunityCard key={card.id || index} card={card} index={index} />;
    case "risks":
      return <RiskCard key={card.id || index} card={card} index={index} />;
    case "recommendations":
      return <RecommendationCard key={card.id || index} card={card} index={index} />;
    case "trends":
      return <TrendCard key={card.id || index} card={card} index={index} />;
    default:
      return <DefaultCard key={card.id || index} card={card} index={index} />;
  }
}

function renderChart(chart: ChartSpec, index: number) {
  const chartActions = (
    <div className="flex items-center gap-1 bg-surface-muted p-1 rounded-xl text-xs">
      <button
        onClick={() => {
          const csvContent = "data:text/csv;charset=utf-8,Label,Value\n" + (chart.data || []).map((d: ChartDataPoint) => `${d.category || d.x || d.name || "Item"},${d.value || d.y || 0}`).join("\n");
          const link = document.createElement("a");
          link.setAttribute("href", encodeURI(csvContent));
          link.setAttribute("download", `${chart.id || `chart-${index + 1}`}.csv`);
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }}
        className="p-2 bg-surface-muted hover:bg-surface-muted border border-border-color rounded-xl text-text-secondary transition-colors flex items-center gap-1 flex-shrink-0"
        aria-label={`Export ${chart.title || "chart"} as CSV`}
      >
        <Download className="w-3.5 h-3.5" />
      </button>
    </div>
  );

  return (
    <motion.div
      key={chart.id || index}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 + index * 0.07, duration: 0.4 }}
    >
      <DynamicChartRenderer key={chart.id || index} chart={chart} />
    </motion.div>
  );
}

export default function DynamicSectionRenderer({ sections }: Props) {
  const nonEmptySections = useMemo(() => {
    if (!sections || sections.length === 0) return [];
    return sections.filter(
      (s) => (s.cards && s.cards.length > 0) || (s.charts && s.charts.length > 0)
    );
  }, [sections]);

  if (nonEmptySections.length === 0) {
    return null;
  }

  return (
    <div className="space-y-6">
      {nonEmptySections.map((section, sIdx) => {
        const Icon = SECTION_ICONS[section.id] || BarChart3;
        const iconColor = SECTION_COLORS[section.id] || "text-primary-600";
        const hasCards = section.cards && section.cards.length > 0;
        const hasCharts = section.charts && section.charts.length > 0;

        if (!hasCards && !hasCharts) return null;

        return (
          <motion.section
            key={section.id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: sIdx * 0.08, duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="premium-card p-6 lg:p-7 space-y-6"
          >
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600 mb-1">
              <Icon className={`w-4 h-4 ${iconColor}`} />
              <span>{section.title}</span>
            </div>
            <h2 className="text-xl font-extrabold text-text-primary">{section.title}</h2>
            {section.description && (
              <p className="text-sm text-text-muted leading-relaxed max-w-3xl">{section.description}</p>
            )}

            {hasCards && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {section.cards.map((card, idx) => renderCardContent(card, section.id, idx))}
              </div>
            )}

            {hasCharts && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {section.charts.map((chart, idx) => renderChart(chart, idx))}
              </div>
            )}
          </motion.section>
        );
      })}
    </div>
  );
}
