"use client";

import React, { useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { formatBusinessValue } from "@/lib/formatting";
import { TrendingUp, HelpCircle } from "lucide-react";
import InsightExplanationModal, { InsightDetail } from "../dashboard/InsightExplanationModal";
import ChartCard from "./ChartCard";

interface ForecastData {
  temporal_column?: string;
  measure_column?: string;
  horizon_periods?: number;
  trend_direction?: string;
  historical?: Array<{ period: string; value: number }>;
  forecast?: Array<{ period: string; forecast_value: number; lower_bound: number; upper_bound: number }>;
  loading?: boolean;
  error?: string | null;
  time_series_points?: Array<{ period: string; historical?: number; forecast?: number; lower_bound?: number; upper_bound?: number }>;
}

const CHART_HEIGHT = 320;

export default function ForecastChartRenderer({ data }: { data: ForecastData }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [activeInsight, setActiveInsight] = useState<InsightDetail | null>(null);

  if (data?.loading) {
    return (
      <ChartCard title="Generating Forecast" subtitle="Machine learning model running" loading>
        <div />
      </ChartCard>
    );
  }

  if (data?.error) {
    return (
      <ChartCard title="Forecast Error" error={data.error}>
        <div />
      </ChartCard>
    );
  }

  if (!data || (!data.historical?.length && !data.forecast?.length)) {
    return (
      <ChartCard
        title="Predictive Forecast"
        subtitle="No data available"
        emptyMessage="Predictive Forecast Unavailable"
        emptyDescription="No historical forecast data is available for this workspace yet."
      >
        <div className="flex flex-col items-center justify-center py-8 text-center space-y-3">
          <div className="p-3 bg-surface-muted text-text-muted rounded-xl border border-border-color">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-text-muted uppercase tracking-wider">Predictive Forecast Unavailable</h4>
            <p className="text-xs text-text-muted mt-1 max-w-sm leading-relaxed">
              No historical forecast data is available for this workspace yet.
            </p>
          </div>
        </div>
      </ChartCard>
    );
  }

  const measureName = data.measure_column || "primary_metric";

  const combined: Array<{ period: string; historical_value: number | null; forecast_value: number | null; confidence_range: [number, number] | null }> = [];
  if (data.time_series_points && data.time_series_points.length > 0) {
    data.time_series_points.forEach((pt) => {
      combined.push({
        period: pt.period,
        historical_value: pt.historical ?? null,
        forecast_value: pt.forecast ?? null,
        confidence_range: (pt.lower_bound != null && pt.upper_bound != null) ? [pt.lower_bound, pt.upper_bound] : null,
      });
    });
  } else {
    (data.historical || []).forEach((h) => {
      combined.push({
        period: h.period,
        historical_value: h.value,
        forecast_value: null,
        confidence_range: null,
      });
    });

    const lastHist = data.historical?.[data.historical.length - 1];
    if (lastHist && data.forecast?.[0]) {
      combined.push({
        period: lastHist.period,
        historical_value: lastHist.value,
        forecast_value: lastHist.value,
        confidence_range: [lastHist.value, lastHist.value],
      });
    }

    (data.forecast || []).forEach((f) => {
      combined.push({
        period: f.period,
        historical_value: null,
        forecast_value: f.forecast_value,
        confidence_range: [f.lower_bound, f.upper_bound],
      });
    });
  }

  const trendColor = data.trend_direction === "UPWARD" ? "var(--success-500)" : data.trend_direction === "DOWNWARD" ? "var(--error-500)" : "var(--primary-500)";

  function openExplanation() {
    setActiveInsight({
      title: `${measureName.replace("_", " ").toUpperCase()} ML Predictive Forecast`,
      why_important: `Predicts future ${measureName.replace("_", " ")} momentum for the next ${data.horizon_periods || 14} periods with a confidence interval band to support operational planning.`,
      how_calculated: "Statistical forecasting model using temporal aggregation on the active dataset.",
      recommended_action: data.trend_direction === "UPWARD"
        ? "Scale up capacity and resources to meet projected demand growth."
        : "Implement mitigation strategies to address projected volume deceleration.",
      business_impact: `Predictive trajectory establishes baseline for planning.`
    });
    setModalOpen(true);
  }

  const forecastHeader = (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
      <div>
        <div className="flex items-center gap-2">
          <h3 className="text-base font-bold text-text-primary">
            {measureName.replace("_", " ").toUpperCase()} {data.horizon_periods || 14}-Period Predictive Forecast
          </h3>
          <button
            onClick={openExplanation}
            className="px-2.5 py-1.5 bg-primary-50 hover:bg-primary-100 text-primary-600 rounded-xl text-xs font-semibold flex items-center gap-1 transition-colors"
          >
            <HelpCircle className="w-3.5 h-3.5" />
            <span>Explain</span>
          </button>
        </div>
        <p className="text-xs text-text-muted mt-0.5">
          Machine Learning Ridge Time-Series Projection with 95% Confidence Interval Band.
        </p>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs text-text-muted font-medium">Trend Trajectory:</span>
        <span
          className={`px-3 py-1 text-xs font-bold rounded-full ${
            data.trend_direction === "UPWARD"
              ? "bg-success-100 text-success-700"
              : data.trend_direction === "DOWNWARD"
              ? "bg-error-100 text-error-700"
              : "bg-primary-100 text-primary-700"
          }`}
        >
          {data.trend_direction || "STABLE"}
        </span>
      </div>
    </div>
  );

  const forecastChart = (
    <div style={{ width: "100%", height: `${CHART_HEIGHT}px` }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={combined} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
          <defs>
            <linearGradient id="forecastBand" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={trendColor} stopOpacity={0.25} />
              <stop offset="95%" stopColor={trendColor} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--chart-grid)" />
          <XAxis dataKey="period" tick={{ fill: "var(--chart-text)", fontSize: 11 }} />
          <YAxis tick={{ fill: "var(--chart-text)", fontSize: 11 }} tickFormatter={(val) => formatBusinessValue(measureName, val)} />
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
            formatter={(val) => [formatBusinessValue(measureName, val), measureName.replace("_", " ")]}
            cursor={{ fill: "var(--hover-bg)", fillOpacity: 0.4 }}
          />
          <Legend wrapperStyle={{ fontSize: "12px", color: "var(--text-secondary)" }} />
          <Area
            type="monotone"
            dataKey="confidence_range"
            stroke="none"
            fill="url(#forecastBand)"
            name="95% Confidence Interval"
          />
          <Line
            type="monotone"
            dataKey="historical_value"
            stroke="var(--info-500)"
            strokeWidth={3}
            dot={{ r: 3, fill: "var(--info-500)", stroke: "var(--surface)", strokeWidth: 1 }}
            activeDot={{ r: 5, fill: "var(--info-500)", stroke: "var(--surface)", strokeWidth: 2 }}
            name="Historical Actual"
          />
          <Line
            type="monotone"
            dataKey="forecast_value"
            stroke={trendColor}
            strokeWidth={3}
            strokeDasharray="5 5"
            dot={{ r: 4, fill: trendColor, stroke: "var(--surface)", strokeWidth: 1 }}
            activeDot={{ r: 6, fill: trendColor, stroke: "var(--surface)", strokeWidth: 2 }}
            name="ML Forecast Projection"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );

  const forecastInsights = (
    <div className="p-4 bg-surface-muted border border-border-color rounded-xl space-y-2 text-xs">
      <div className="flex items-center justify-between font-bold text-text-primary">
        <span>Executive Forecast Interpretation:</span>
        <span className="text-success-700 font-mono text-[11px]">95% Statistical Confidence</span>
      </div>
      <p className="text-text-secondary leading-relaxed">
        The machine learning model predicts a <strong>{data.trend_direction || "STABLE"}</strong> trajectory for {measureName.replace("_", " ")} across the upcoming {data.horizon_periods || 14} periods. Confidence interval shaded band represents expected upper and lower variance bounds.
      </p>
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
        title={`${measureName.replace("_", " ").toUpperCase()} Forecast`}
        subtitle={`${data.horizon_periods || 14}-Period Projection`}
        header={forecastHeader}
        footer={forecastInsights}
      >
        {forecastChart}
      </ChartCard>
    </>
  );
}
