"use client";

import React, { useState, useEffect } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  LineChart,
  Line,
} from "recharts";
import { formatBusinessValue } from "@/lib/formatting";
import type { ChartSpec, ChartDataPoint, MetricObject } from "@/lib/types";
import {
  BarChart3,
  LineChart as LineIcon,
  PieChart as PieIcon,
  Activity,
  HelpCircle,
  Info,
  Download,
  Maximize2,
  Minimize2,
  ArrowUpDown,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";
import InsightExplanationModal, { InsightDetail } from "../dashboard/InsightExplanationModal";
import ChartCard from "./ChartCard";

const COLORS = ["var(--primary-500)", "var(--chart-secondary)", "var(--success-500)", "var(--warning-500)", "var(--error-500)", "var(--primary-600)", "var(--info-500)", "var(--chart-secondary)"];

const CHART_HEIGHT = 320;

export default function DynamicChartRenderer({ chart }: { chart: ChartSpec }) {
  const initialType = chart?.type === "horizontal_bar" ? "bar" : (chart?.type || "bar");
  const validType: "area" | "bar" | "pie" | "line" = (["area", "bar", "pie", "line"] as const).includes(initialType as "area" | "bar" | "pie" | "line") ? initialType as "area" | "bar" | "pie" | "line" : "bar";
  const [currentType, setCurrentType] = useState<"area" | "bar" | "pie" | "line">(validType);
  const [modalOpen, setModalOpen] = useState(false);
  const [fullScreen, setFullScreen] = useState(false);
  const [sortAsc, setSortAsc] = useState(false);
  const [activeInsight, setActiveInsight] = useState<InsightDetail | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || chart?.loading) {
    return (
      <ChartCard title={chart?.title || "Visualization"} loading>
        <div className="h-[320px] w-full flex items-center justify-center animate-pulse bg-surface-muted/30 rounded-xl" />
      </ChartCard>
    );
  }

  if (chart?.error) {
    return (
      <ChartCard title={chart?.title || "Visualization"} error={chart.error}>
        <div />
      </ChartCard>
    );
  }

  if (!chart || chart.available === false || !chart.data || chart.data.length === 0) {
    return (
      <ChartCard
        title={chart?.title || "Visualization"}
        subtitle="Data unavailable"
        empty
        emptyMessage={`${chart?.title || "Visualization"} Unavailable`}
        emptyDescription={chart?.reason || "This visualization cannot be displayed because the dataset is missing the required columns."}
        emptyIcon={
          <div className="p-3 bg-surface-muted text-text-muted rounded-xl border border-border-color">
            <BarChart3 className="w-5 h-5" />
          </div>
        }
      >
        <div />
      </ChartCard>
    );
  }

  const xKey = chart.x_axis || chart.category_key || "category";
  const yKey = chart.y_axis || chart.value_key || "value";
  const isTimeSeries = chart.type === "area" || chart.type === "line";

  function getItemLabel(item: ChartDataPoint | null | undefined): string {
    if (!item) return "N/A";
    const raw = item.label ?? item.x_field ?? item.category ?? item.period ?? item[xKey];
    if (raw !== undefined && raw !== null && String(raw).trim() !== "" && String(raw).trim() !== "undefined") {
      return String(raw);
    }
    return "N/A";
  }

  function getItemValue(item: ChartDataPoint | null | undefined): number {
    if (!item) return 0;
    const raw = item.value ?? item.y_field ?? item.frequency ?? item[yKey];
    if (typeof raw === "object" && raw !== null) {
      const m = raw as MetricObject;
      return typeof m.value === "number" ? m.value : (typeof m.formatted_value === "string" ? parseFloat(m.formatted_value.replace(/[^0-9.-]/g, "")) || 0 : 0);
    }
    const num = Number(raw);
    return !isNaN(num) ? num : 0;
  }

  const sortedData = [...chart.data].sort((a, b) => {
    const valA = getItemValue(a);
    const valB = getItemValue(b);
    return sortAsc ? valA - valB : valB - valA;
  });

  const topItem = sortedData[0] || {};
  const topLabel = getItemLabel(topItem);
  const topVal = getItemValue(topItem);

  const explanation = isTimeSeries
    ? `Temporal analysis across ${chart.data.length} periods. Peak value recorded at '${topLabel}' with ${formatBusinessValue(yKey, topVal)}.`
    : `Comparative analysis across ${chart.data.length} categories. '${topLabel}' leads with ${formatBusinessValue(yKey, topVal)}.`;

  const riskColor = chart.risk_level === "HIGH" || chart.risk_level === "CRITICAL" ? "error" : chart.risk_level === "MEDIUM" ? "warning" : "success";

  function exportChartCSV() {
    if (!sortedData || sortedData.length === 0) return;
    const headers = "Category,Value";
    const rows = sortedData.map((d) => `"${getItemLabel(d)}",${getItemValue(d)}`).join("\n");
    const csvContent = "data:text/csv;charset=utf-8," + encodeURIComponent(`${headers}\n${rows}`);
    const link = document.createElement("a");
    link.setAttribute("href", csvContent);
    link.setAttribute("download", `${chart.id || "chart_data"}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function openExplanation() {
    setActiveInsight({
      title: chart.title,
      why_important: chart.ai_interpretation || `Visualizes distribution and concentration across '${xKey}'. Helps leadership identify key drivers and low-volume segments.`,
      how_calculated: `Analytics computation: SELECT ${xKey}, SUM(${yKey}) FROM read_parquet('active_dataset') GROUP BY ${xKey} ORDER BY SUM(${yKey}) DESC`,
      recommended_action: chart.recommendation || `Investigate top performer '${topLabel}' and review low-performing segments for optimization opportunities.`,
      business_impact: chart.business_impact || `Top category '${topLabel}' contributes significant share to total volume.`
    });
    setModalOpen(true);
  }

  const chartContent = (
    <>
      <div style={{ width: "100%", height: fullScreen ? "65vh" : `${CHART_HEIGHT}px` }}>
        <ResponsiveContainer width="100%" height="100%">
          {currentType === "area" ? (
            <AreaChart data={sortedData} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
              <defs>
                <linearGradient id={`color-${chart.id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--primary-500)" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="var(--primary-500)" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--chart-grid)" />
              <XAxis dataKey="label" tick={{ fill: "var(--chart-text)", fontSize: 11 }} />
              <YAxis tick={{ fill: "var(--chart-text)", fontSize: 11 }} tickFormatter={(val) => formatBusinessValue("value", val)} />
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
                formatter={(val) => [formatBusinessValue("value", val), "Value"]}
                cursor={{ fill: "var(--hover-bg)", fillOpacity: 0.4 }}
              />
              <Legend wrapperStyle={{ fontSize: "12px", color: "var(--text-secondary)" }} />
              <Area type="monotone" dataKey="value" stroke="var(--primary-500)" strokeWidth={3} fillOpacity={1} fill={`url(#color-${chart.id})`} name="Value" dot={{ r: 4, fill: "var(--primary-500)", stroke: "var(--surface)", strokeWidth: 2 }} activeDot={{ r: 6, fill: "var(--primary-500)", stroke: "var(--surface)", strokeWidth: 2 }} />
            </AreaChart>
          ) : currentType === "line" ? (
            <LineChart data={sortedData} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--chart-grid)" />
              <XAxis dataKey="label" tick={{ fill: "var(--chart-text)", fontSize: 11 }} />
              <YAxis tick={{ fill: "var(--chart-text)", fontSize: 11 }} tickFormatter={(val) => formatBusinessValue("value", val)} />
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
                formatter={(val) => [formatBusinessValue("value", val), "Value"]}
                cursor={{ fill: "var(--hover-bg)", fillOpacity: 0.4 }}
              />
              <Legend wrapperStyle={{ fontSize: "12px", color: "var(--text-secondary)" }} />
              <Line type="monotone" dataKey="value" stroke="var(--chart-secondary)" strokeWidth={3} dot={{ r: 4, fill: "var(--chart-secondary)" }} activeDot={{ r: 6, fill: "var(--chart-secondary)", stroke: "var(--surface)", strokeWidth: 2 }} name="Value" />
            </LineChart>
          ) : currentType === "pie" ? (
            <PieChart>
              <Tooltip
                contentStyle={{
                  background: "var(--surface)",
                  border: "1px solid var(--border-color)",
                  borderRadius: "12px",
                  boxShadow: "var(--shadow-md)",
                  padding: "10px 14px",
                }}
                labelStyle={{ color: "var(--text-primary)", fontWeight: 600, fontSize: "11px" }}
                itemStyle={{ color: "var(--text-secondary)", fontSize: "12px" }}
                formatter={(val) => [formatBusinessValue("value", val), "Value"]}
              />
              <Legend wrapperStyle={{ fontSize: "12px", color: "var(--text-secondary)" }} />
              <Pie
                data={sortedData}
                dataKey="value"
                nameKey="label"
                cx="50%"
                cy="50%"
                outerRadius={Math.min(120, CHART_HEIGHT / 2.5)}
                innerRadius={Math.min(60, CHART_HEIGHT / 5)}
                paddingAngle={4}
                stroke="none"
              >
                {sortedData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          ) : (
            <BarChart data={sortedData} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--chart-grid)" />
              <XAxis dataKey="label" tick={{ fill: "var(--chart-text)", fontSize: 11 }} />
              <YAxis tick={{ fill: "var(--chart-text)", fontSize: 11 }} tickFormatter={(val) => formatBusinessValue("value", val)} />
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
                formatter={(val) => [formatBusinessValue("value", val), "Value"]}
                cursor={{ fill: "var(--hover-bg)", fillOpacity: 0.4 }}
              />
              <Legend wrapperStyle={{ fontSize: "12px", color: "var(--text-secondary)" }} />
              <Bar dataKey="value" fill="var(--primary-500)" radius={[6, 6, 0, 0]} name="Value" />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </>
  );

  const chartActions = (
    <>
      <div className="flex items-center gap-1 bg-surface-muted p-1 rounded-xl text-xs">
        <button
          onClick={() => setCurrentType("bar")}
          className={`px-2 py-1 rounded-lg transition-all flex items-center gap-1 font-semibold ${
            currentType === "bar" ? "bg-primary-50 text-primary-700 font-semibold" : "text-text-muted hover:text-text-primary"
          }`}
          aria-label="Bar chart"
        >
          <BarChart3 className="w-3.5 h-3.5" />
          <span>Bar</span>
        </button>
        <button
          onClick={() => setCurrentType("area")}
          className={`px-2 py-1 rounded-lg transition-all flex items-center gap-1 font-semibold ${
            currentType === "area" ? "bg-primary-50 text-primary-700 font-semibold" : "text-text-muted hover:text-text-primary"
          }`}
          aria-label="Area chart"
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Area</span>
        </button>
        <button
          onClick={() => setCurrentType("line")}
          className={`px-2 py-1 rounded-lg transition-all flex items-center gap-1 font-semibold ${
            currentType === "line" ? "bg-primary-50 text-primary-700 font-semibold" : "text-text-muted hover:text-text-primary"
          }`}
          aria-label="Line chart"
        >
          <LineIcon className="w-3.5 h-3.5" />
          <span>Line</span>
        </button>
        <button
          onClick={() => setCurrentType("pie")}
          className={`px-2 py-1 rounded-lg transition-all flex items-center gap-1 font-semibold ${
            currentType === "pie" ? "bg-primary-50 text-primary-700 font-semibold" : "text-text-muted hover:text-text-primary"
          }`}
          aria-label="Pie chart"
        >
          <PieIcon className="w-3.5 h-3.5" />
          <span>Pie</span>
        </button>
      </div>

      <button
        onClick={() => setSortAsc(!sortAsc)}
        title="Toggle Sort Direction"
        className="p-1.5 bg-surface-muted hover:bg-border-color text-text-secondary rounded-lg text-xs font-medium transition-colors"
      >
        <ArrowUpDown className="w-3.5 h-3.5" />
      </button>

      <button
        onClick={exportChartCSV}
        title="Export CSV Data"
        className="p-1.5 bg-surface-muted hover:bg-border-color text-text-secondary rounded-lg text-xs font-medium transition-colors"
      >
        <Download className="w-3.5 h-3.5" />
      </button>

      <button
        onClick={() => setFullScreen(!fullScreen)}
        title="Toggle Fullscreen"
        className="p-1.5 bg-surface-muted hover:bg-border-color text-text-secondary rounded-lg text-xs font-medium transition-colors"
      >
        {fullScreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
      </button>
    </>
  );

  const aiSummaryFooter = (
    <div className="p-4 bg-surface-muted border border-border-color rounded-xl text-xs text-text-secondary space-y-3">
      <div className="flex items-start gap-2.5">
        <Info className="w-4 h-4 text-primary-600 mt-0.5 flex-shrink-0" />
        <div className="leading-relaxed flex-1">
          <strong className="text-text-primary block mb-0.5">Executive Business Summary:</strong>
          <span>{chart.ai_interpretation || explanation}</span>
        </div>
      </div>

      {(chart.business_impact || chart.risk_level || chart.opportunity || chart.recommendation || chart.confidence) && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t border-border-color">
          {chart.business_impact && (
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">Business Impact</span>
              <p className="text-[11px] text-text-secondary font-medium leading-relaxed">{chart.business_impact}</p>
            </div>
          )}
          {chart.risk_level && (
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">Risk Level</span>
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-${riskColor}-50 text-${riskColor}-700 border border-${riskColor}-200`}>
                <AlertTriangle className="w-3 h-3" />
                {chart.risk_level}
              </span>
            </div>
          )}
          {chart.opportunity && (
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">Opportunity</span>
              <p className="text-[11px] text-success-700 font-medium leading-relaxed">{chart.opportunity}</p>
            </div>
          )}
          {chart.recommendation && (
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">Recommendation</span>
              <p className="text-[11px] text-primary-700 font-medium leading-relaxed">{chart.recommendation}</p>
            </div>
          )}
        </div>
      )}

      {(chart.confidence || chart.evidence) && (
        <div className="flex items-center gap-4 pt-2 border-t border-border-color text-[11px]">
          {chart.confidence && (
            <span className="flex items-center gap-1.5 font-bold text-success-700">
              <ShieldCheck className="w-3.5 h-3.5" />
              {chart.confidence} Confidence
            </span>
          )}
          {chart.evidence && (
            <span className="text-text-muted font-mono truncate">{chart.evidence}</span>
          )}
        </div>
      )}
    </div>
  );

  return (
    <>
      <InsightExplanationModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        insight={activeInsight}
      />
      <ChartCard
        title={chart.title}
        subtitle={`${chart.data.length} data points`}
        actions={chartActions}
        footer={aiSummaryFooter}
        className={fullScreen ? "fixed inset-4 z-50 overflow-y-auto max-h-[95vh] shadow-2xl border-border-strong" : ""}
      >
        {chartContent}
      </ChartCard>
    </>
  );
}
