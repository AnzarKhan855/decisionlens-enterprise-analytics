export interface MetricObject {
  name: string;
  formatted_value: string;
  value: number | string;
  confidence: number | string;
  metric_type?: string;
  [key: string]: unknown;
}

export function isMetricObject(obj: unknown): obj is MetricObject {
  return (
    typeof obj === "object" &&
    obj !== null &&
    typeof (obj as Record<string, unknown>).name === "string" &&
    typeof (obj as Record<string, unknown>).formatted_value === "string" &&
    "value" in (obj as Record<string, unknown>) &&
    typeof (obj as Record<string, unknown>).confidence === "number" ||
    typeof (obj as Record<string, unknown>).confidence === "string"
  );
}

export function getMetricDisplayValue(metric: unknown): string {
  if (typeof metric === "string") return metric;
  if (typeof metric === "number") return String(metric);
  if (metric && typeof metric === "object") {
    const m = metric as Record<string, unknown>;
    if (typeof m.formatted_value === "string") return m.formatted_value;
    if (typeof m.value !== "undefined" && m.value !== null) {
      if (typeof m.value === "string") return m.value;
      if (typeof m.value === "number") return String(m.value);
      if (typeof m.value === "object") return getMetricDisplayValue(m.value);
    }
    if (typeof m.name === "string") return m.name;
  }
  return "N/A";
}

export function getMetricNumericValue(metric: unknown): number {
  if (typeof metric === "number") return metric;
  if (typeof metric === "string") {
    const cleaned = metric.replace(/[^0-9.-]/g, "");
    const parsed = parseFloat(cleaned);
    return isNaN(parsed) ? 0 : parsed;
  }
  if (metric && typeof metric === "object") {
    const m = metric as Record<string, unknown>;
    if (typeof m.value === "number") return m.value;
    if (typeof m.value === "string") {
      const cleaned = m.value.replace(/[^0-9.-]/g, "");
      const parsed = parseFloat(cleaned);
      return isNaN(parsed) ? 0 : parsed;
    }
    if (typeof m.formatted_value === "string") {
      const cleaned = m.formatted_value.replace(/[^0-9.-]/g, "");
      const parsed = parseFloat(cleaned);
      return isNaN(parsed) ? 0 : parsed;
    }
  }
  return 0;
}

export function getMetricConfidence(metric: unknown): number {
  if (typeof metric === "number") return metric;
  if (typeof metric === "string") {
    const cleaned = metric.replace(/[^0-9.]/g, "");
    const parsed = parseFloat(cleaned);
    return isNaN(parsed) ? 0 : parsed;
  }
  if (metric && typeof metric === "object") {
    const m = metric as Record<string, unknown>;
    if (typeof m.confidence === "number") return m.confidence;
    if (typeof m.confidence === "string") {
      const cleaned = m.confidence.replace(/[^0-9.]/g, "");
      const parsed = parseFloat(cleaned);
      return isNaN(parsed) ? 0 : parsed;
    }
  }
  return 0;
}

export function getMetricName(metric: unknown): string {
  if (typeof metric === "string") return metric;
  if (metric && typeof metric === "object") {
    const m = metric as Record<string, unknown>;
    if (typeof m.name === "string") return m.name;
    if (typeof m.metric_type === "string") return m.metric_type;
  }
  return "Unknown Metric";
}

export interface DashboardPayload {
  kpis: MetricObject[];
  sections: DashboardSection[];
  charts: ChartSpec[];
  executive_briefing?: ExecutiveBriefing;
  executive_story?: string;
  executive_newsfeed?: NewsItem[];
  action_center?: ActionItem[];
  multi_agent_reports?: AgentReport[];
  intelligence?: IntelligenceData;
  predictions?: PredictionItem[];
  health_score?: number;
  dataset_id?: string;
  dataset_type?: string;
  profile?: DatasetProfile;
  is_lookup_only?: boolean;
  lookup_table_warning?: LookupWarning;
  workspace_exists?: boolean;
  error_details?: Record<string, unknown>;
  readiness?: { readiness_score: number; readiness_level: string };
  connected_tables_count?: number;
}

export interface ExecutiveBriefing {
  greeting: string;
  business_name: string;
  health_score: number;
  primary_metric: string;
  status: string;
  main_opportunity: string;
  biggest_risk: string;
  forecast: string;
  ai_confidence: string;
}

export interface NewsItem {
  time: string;
  title: string;
  impact: string;
  body: string;
}

export interface ActionItem {
  id: number;
  priority: string;
  action: string;
  expected_roi: string;
  confidence: string;
  time: string;
  difficulty: string;
  owner: string;
  evidence_sql: string;
  explanation: string;
}

export interface AgentReport {
  agent: string;
  focus: string;
  finding: string;
  recommendation: string;
  impact: string;
  confidence: string;
}

export interface IntelligenceData {
  domain: string;
  business_questions: string[];
}

export interface PredictionItem {
  metric: string;
  model_type: string;
  prediction: string;
  predicted_value: number;
  current_value: number;
  confidence: number;
  horizon: string;
  time_series_points?: TimeSeriesPoint[];
}

export interface TimeSeriesPoint {
  period: string;
  historical?: number;
  forecast?: number;
  lower_bound?: number;
  upper_bound?: number;
}

export interface DatasetProfile {
  total_rows?: number;
  total_columns?: number;
}

export interface LookupWarning {
  title: string;
  message: string;
  required_datasets?: string[];
}

export interface ChartSpec {
  id: string;
  type: string;
  title: string;
  description?: string;
  data: ChartDataPoint[];
  loading?: boolean;
  error?: string | null;
  available?: boolean;
  reason?: string;
  required_columns?: string[];
  x_axis?: string;
  y_axis?: string;
  category_key?: string;
  value_key?: string;
  ai_interpretation?: string;
  business_impact?: string;
  risk_level?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  opportunity?: string;
  recommendation?: string;
  confidence?: string;
  evidence?: string;
}

export interface ChartDataPoint {
  label?: string;
  category?: string;
  x?: string;
  x_field?: string;
  y_field?: string;
  name?: string;
  period?: string;
  value: number | string;
  y?: number;
  frequency?: number;
  [key: string]: unknown;
}

export interface DashboardSection {
  id: string;
  title: string;
  description: string;
  order: number;
  cards: SectionCard[];
  charts: ChartSpec[];
  metadata: Record<string, unknown>;
}

export interface SectionCard {
  id: string;
  title: string;
  category?: string;
  severity?: string;
  description?: string;
  impact?: string;
  action?: string;
  timeline?: string;
  reason?: string;
  recommended_action?: string;
  expected_roi?: string;
  trend?: string;
  status?: string;
  metric_type?: string;
  data_points?: number;
  latest_value?: number;
  latest_change_pct?: number;
  direction?: string;
  chart_data?: ChartDataPoint[];
  name?: string;
  formatted_value?: string;
  value?: string | number;
  source_column?: string;
  formula?: string;
  rows_analyzed?: number;
  confidence?: number;
  available?: boolean;
  insight?: string;
  trend_value?: string;
  change_pct?: number;
  comparison_period?: string;
  data_source?: string;
  period?: string;
  metric?: string;
  actual_value?: number;
  expected_value?: number;
  top_driver?: { category?: string; contribution_percentage?: number };
  winner?: string;
  difference_pct?: number;
  model_type?: string;
  model_used?: string;
  prediction?: string;
  time_horizon?: string;
  priority?: string;
  mitigation?: string;
  measure?: string;
  [key: string]: unknown;
}

export interface KPICardItem {
  name: string;
  value: string;
  formatted_value: string;
  metric_type: string;
  source_column: string;
  formula: string;
  rows_analyzed: number;
  confidence: number;
  available: boolean;
  status: string;
  insight: string;
  trend_value: string;
  change_pct?: number;
  comparison_period: string;
  data_source: string;
}
