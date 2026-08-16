import { getCached } from "./api";
import type { MetricObject } from "./types";

export interface CopilotResponse {
  executive_summary: string;
  evidence: Array<Record<string, unknown> | string>;
  confidence_score: number;
  sql_used?: string | null;
  datasets_used: string[];
  tables_used: string[];
  columns_used: string[];
  kpis_used: Array<string | MetricObject>;
  business_reasoning: string;
  follow_up_questions: string[];
  charts: Array<{ id: string; title: string; available: boolean }>;
  recommendation: { title: string; actions: string[]; risks?: string[]; opportunities?: string[] };
  validation: { status: string; rows_returned: number };
  error?: string | null;
  intent: string;
  domain: string;
  timestamp: string;
}

export interface CopilotMessage {
  role: "user" | "assistant" | "system";
  content: string;
  metadata?: {
    intent?: string;
    confidence?: number;
    tables?: string[];
    sql?: string;
  };
  response?: CopilotResponse;
}

export interface ConversationTurn {
  role: "user" | "assistant";
  content: string;
  intent?: string;
  confidence?: number;
  entities?: string[];
  metrics?: string[];
  timestamp?: string;
}

export interface WorkspaceOption {
  workspace_id: string;
  name: string;
  industry?: string;
  is_active?: boolean;
}

export interface DatasetOption {
  id: string;
  name: string;
  description?: string;
  dataset_type?: string;
  rows?: number;
}

export async function listWorkspaces(): Promise<WorkspaceOption[]> {
  try {
    const res = await getCached<unknown>("/workspaces", undefined, 0);
    const list = (res as { workspaces?: unknown[] } | undefined)?.workspaces || [];
    return list.map((w) => ({
      workspace_id: (w as { workspace_id: string }).workspace_id,
      name: (w as { name?: string }).name || (w as { workspace_id: string }).workspace_id,
      industry: (w as { industry?: string }).industry,
      is_active: (w as { is_active?: boolean }).is_active,
    }));
  } catch {
    return [];
  }
}

export async function listDatasets(): Promise<DatasetOption[]> {
  try {
    const res = await getCached<unknown>("/datasets", undefined, 0);
    const list = (res as { datasets?: unknown[] } | undefined)?.datasets || [];
    return list.map((d) => ({
      id: String((d as { id: unknown }).id),
      name: (d as { name?: string }).name || (d as { filename?: string }).filename || String((d as { id: unknown }).id),
      description: (d as { description?: string }).description,
      dataset_type: (d as { dataset_type?: string }).dataset_type,
      rows: (d as { rows?: number }).rows,
    }));
  } catch {
    return [];
  }
}

export async function askCopilot(
  question: string,
  sessionId: string = "default",
  workspaceId?: string,
  includeSql: boolean = true,
  conversationHistory?: ConversationTurn[],
  datasetId?: string,
  retries: number = 2,
): Promise<CopilotResponse> {
  const maxRetries = Math.max(0, retries);
  let lastError: unknown = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const { default: api } = await import("./api");
      const res = await api.post("/ai/copilot/query", {
        question,
        session_id: sessionId,
        workspace_id: workspaceId,
        dataset_id: datasetId,
        include_sql: includeSql,
        conversation_history: conversationHistory || [],
      });
      return res.data;
    } catch (err) {
      lastError = err;
      const isLastAttempt = attempt === maxRetries;
      if (isLastAttempt) break;
      const delay = Math.min(1000 * 2 ** attempt, 5000);
      await new Promise((r) => setTimeout(r, delay));
    }
  }

  const errorMessage = lastError instanceof Error ? lastError.message : "DecisionLens could not complete the analysis.";
  const sanitized = errorMessage.replace(/\n+/g, " ").trim();
  const fallback: CopilotResponse = {
    executive_summary: "DecisionLens could not complete this analysis. The analytics service returned an error.",
    evidence: ["The analytics service returned an error."],
    confidence_score: 0.0,
    sql_used: null,
    datasets_used: [],
    tables_used: [],
    columns_used: [],
    kpis_used: [],
    business_reasoning: sanitized || "The analysis system encountered an issue. Please verify backend connectivity and active workspace.",
    follow_up_questions: ["Retry the question", "Check backend status", "Verify workspace data"],
    charts: [],
    recommendation: { title: "Error Recovery", actions: ["Retry", "Check backend"] },
    validation: { status: "ERROR", rows_returned: 0 },
    error: sanitized,
    intent: "error",
    domain: "Unknown",
    timestamp: new Date().toISOString(),
  };
  return fallback;
}

export async function resetCopilotSession(sessionId: string = "default"): Promise<void> {
  const { apiPost } = await import("./api");
  await apiPost("/ai/copilot/reset", { session_id: sessionId });
}
