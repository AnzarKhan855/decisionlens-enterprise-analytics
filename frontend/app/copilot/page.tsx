"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  askCopilot,
  resetCopilotSession,
  listWorkspaces,
  listDatasets,
  type CopilotResponse,
  type CopilotMessage,
  type WorkspaceOption,
  type DatasetOption,
} from "@/lib/copilot";
import { getMetricDisplayValue } from "@/lib/types";
import api from "@/lib/api";
import {
  Bot,
  Send,
  Sparkles,
  Database,
  ShieldCheck,
  History,
  AlertTriangle,
  Copy,
  BarChart3,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  Target,
  Pin,
  Download,
  PanelLeftClose,
  PanelLeftOpen,
  Loader2,
  RefreshCw,
  Building2,
  FileText,
} from "lucide-react";

interface Session {
  id: string;
  title: string;
  timestamp: string;
  pinned?: boolean;
}

interface LocalConversationTurn {
  role: "user" | "assistant";
  content: string;
  intent?: string;
  confidence?: number;
  entities?: string[];
  metrics?: string[];
  timestamp?: string;
}

const SUGGESTED_QUESTIONS = [
  "What are the key metrics in this dataset?",
  "Show me trends and patterns over time.",
  "Are there any anomalies or outliers?",
  "What are the root causes of recent changes?",
  "Generate predictions for the next period.",
  "Provide actionable recommendations based on the data.",
];

function renderEvidenceValue(ev: unknown): React.ReactNode {
  if (typeof ev === "string") return ev;
  if (ev && typeof ev === "object") {
    const row = ev as Record<string, unknown>;
    const parts = Object.entries(row)
      .filter(([, val]) => val !== null && val !== undefined)
      .map(([key, val]) =>
        `${key}: ${typeof val === "object" ? JSON.stringify(val) : String(val)}`
      );
    return <span>{parts.join(" | ")}</span>;
  }
  return String(ev);
}

function renderSimpleMarkdown(text: string): React.ReactNode[] {
  if (!text) return [];
  const blocks = text.split(/\n\s*\n/);
  return blocks.map((block, bi) => {
    const trimmed = block.trim();
    if (!trimmed) return null;
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      const items = trimmed.split(/\n/).filter((l) => l.trim().startsWith("- ") || l.trim().startsWith("* "));
      return (
        <ul key={bi} className="list-disc pl-5 space-y-1 my-2">
          {items.map((item, i) => (
            <li key={i}>{renderInlineMarkdown(item.replace(/^[-*]\s+/, ""))}</li>
          ))}
        </ul>
      );
    }
    if (/^\d+\.\s/.test(trimmed)) {
      const items = trimmed.split(/\n/).filter((l) => /^\d+\.\s/.test(l.trim()));
      return (
        <ol key={bi} className="list-decimal pl-5 space-y-1 my-2">
          {items.map((item, i) => (
            <li key={i}>{renderInlineMarkdown(item.replace(/^\d+\.\s+/, ""))}</li>
          ))}
        </ol>
      );
    }
    if (trimmed.includes("|")) {
      const rows = trimmed.split(/\n/).filter((r) => r.trim().includes("|"));
      if (rows.length > 1) {
        return (
          <div key={bi} className="overflow-x-auto my-2">
            <table className="w-full text-xs border border-border-color rounded-xl overflow-hidden">
              <thead>
                <tr className="bg-surface-muted">
                  {rows[0].split("|").filter(Boolean).map((h, j) => (
                    <th key={j} className="px-2 py-1.5 text-left font-bold text-text-secondary border-b border-border-color">
                      {h.trim()}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.slice(2).map((row, ri) => (
                  <tr key={ri} className="border-b border-border-light last:border-0">
                    {row.split("|").filter(Boolean).map((cell, ci) => (
                      <td key={ci} className="px-2 py-1.5 text-text-secondary">{cell.trim()}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
    }
    return <p key={bi} className="my-1">{renderInlineMarkdown(trimmed)}</p>;
  });
}

function renderInlineMarkdown(text: string): React.ReactNode {
  const parts = text.split(/(\*\*.*?\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="font-semibold text-text-primary">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={i} className="px-1.5 py-0.5 bg-surface-muted border border-border-color rounded text-[11px] font-mono text-text-primary">{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-2 h-2 bg-primary-600 rounded-full"
          animate={{ y: [0, -6, 0], opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
        />
      ))}
    </div>
  );
}

function CollapsibleCard({
  title,
  icon,
  children,
  defaultOpen = false,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-border-color rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-surface-muted hover:bg-surface-muted transition-colors text-xs font-semibold text-text-secondary"
      >
        {icon}
        <span className="flex-1 text-left">{title}</span>
        {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3 py-2 text-xs text-text-secondary space-y-1.5 border-t border-border-light">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface ChartItem {
  id: string;
  title: string;
  available: boolean;
}

function ChartPreview({ chart }: { chart: ChartItem }) {
  if (!chart?.available) return null;
  return (
    <div className="p-3 rounded-xl bg-surface-muted border border-border-color text-xs">
      <p className="font-semibold text-text-secondary mb-1">{chart.title}</p>
      <div className="h-24 w-full bg-surface rounded-lg border border-border-light flex items-center justify-center text-text-muted">
        <BarChart3 className="w-6 h-6" />
      </div>
      <p className="text-text-muted mt-1.5 text-[11px]">Ready for review</p>
    </div>
  );
}

export default function AICopilotPage() {
  const [messages, setMessages] = useState<CopilotMessage[]>([
    {
      role: "assistant",
      content:
        "I am your Enterprise AI Copilot. I analyze your active workspace to provide evidence-based answers. Ask me any business question.",
      response: {
        executive_summary:
          "Enterprise AI Copilot is ready. Select an active workspace and ask a business question.",
        evidence: ["Analysis system operational", "Awaiting user query"],
        confidence_score: 1.0,
        sql_used: null,
        datasets_used: [],
        tables_used: [],
        columns_used: [],
        kpis_used: [],
        business_reasoning: "No query has been executed yet.",
        follow_up_questions: SUGGESTED_QUESTIONS.slice(0, 3),
        charts: [],
        recommendation: { title: "Get Started", actions: ["Ask a business question", "Upload data if no workspace is active"] },
        validation: { status: "IDLE", rows_returned: 0 },
        error: null,
        intent: "greeting",
        domain: "System",
        timestamp: new Date().toISOString(),
      },
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeResponse, setActiveResponse] = useState<CopilotResponse | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showEvidencePanel, setShowEvidencePanel] = useState(false);
  const [pinnedResponses, setPinnedResponses] = useState<Record<number, boolean>>({});
  const [sessions, setSessions] = useState<Session[]>([
    { id: "current", title: "Current Session", timestamp: new Date().toISOString(), pinned: true },
  ]);
  const [sessionId] = useState(() => `sess-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  const [conversationHistory, setConversationHistory] = useState<LocalConversationTurn[]>([]);
  const [workspaces, setWorkspaces] = useState<WorkspaceOption[]>([]);
  const [datasets, setDatasets] = useState<DatasetOption[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>("");
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    (async () => {
      const wsList = await listWorkspaces();
      setWorkspaces(wsList);
      const storedWs = typeof window !== "undefined" ? localStorage.getItem("decisionlens_active_workspace") : null;
      const activeWs = (storedWs && wsList.some((w) => w.workspace_id === storedWs) ? storedWs : null) || wsList.find((w) => w.is_active)?.workspace_id || (wsList.length > 0 ? wsList[0].workspace_id : "");
      setSelectedWorkspaceId(activeWs);
      const dsList = await listDatasets();
      setDatasets(dsList);
    })();

    const handleWsChange = (e: any) => {
      const newWs = e?.detail?.workspace_id || (typeof window !== "undefined" ? localStorage.getItem("decisionlens_active_workspace") : null);
      if (newWs) setSelectedWorkspaceId(newWs);
    };
    window.addEventListener("decisionlens:workspace_changed", handleWsChange);
    return () => window.removeEventListener("decisionlens:workspace_changed", handleWsChange);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = useCallback(
    async (text?: string) => {
      const q = (text || input).trim();
      if (!q || loading) return;
      setInput("");

      const userMsg: CopilotMessage = { role: "user", content: q };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      const turn: LocalConversationTurn = {
        role: "user",
        content: q,
        timestamp: new Date().toISOString(),
      };
      setConversationHistory((prev) => [...prev, turn]);

      try {
        const response = await askCopilot(q, sessionId, selectedWorkspaceId || undefined, true, conversationHistory, selectedDatasetId || undefined, 2);
        const assistantMsg: CopilotMessage = {
          role: "assistant",
          content: response.executive_summary,
          metadata: {
            intent: response.intent,
            confidence: response.confidence_score,
            tables: response.tables_used,
            sql: response.sql_used || undefined,
          },
          response,
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setActiveResponse(response);
        setSessions((prev) => [
          { id: `sess-${Date.now()}`, title: q.slice(0, 40), timestamp: new Date().toISOString(), pinned: false },
          ...prev.slice(0, 19),
        ]);
        setConversationHistory((prev) => [
          ...prev,
          {
            role: "assistant",
            content: response.executive_summary,
            intent: response.intent,
            confidence: response.confidence_score,
            timestamp: new Date().toISOString(),
          },
        ]);
      } catch {
        const displayError = "DecisionLens could not complete the analysis.";
        const fallback: CopilotResponse = {
          executive_summary: displayError,
          evidence: [displayError],
          confidence_score: 0.0,
          sql_used: null,
          datasets_used: [],
          tables_used: [],
          columns_used: [],
          kpis_used: [],
          business_reasoning: "The analysis system encountered an issue. Please verify backend connectivity and active workspace.",
          follow_up_questions: ["Retry the question", "Check backend status", "Verify workspace data"],
          charts: [],
          recommendation: { title: "Error Recovery", actions: ["Retry", "Check backend"] },
          validation: { status: "ERROR", rows_returned: 0 },
          error: displayError,
          intent: "error",
          domain: "Unknown",
          timestamp: new Date().toISOString(),
        };
        const assistantMsg: CopilotMessage = {
          role: "assistant",
          content: "DecisionLens could not complete the analysis.",
          response: fallback,
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setActiveResponse(fallback);
        setConversationHistory((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "DecisionLens could not complete the analysis.",
            intent: "error",
            confidence: 0.0,
            timestamp: new Date().toISOString(),
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [input, loading, sessionId, conversationHistory, selectedWorkspaceId, selectedDatasetId]
  );

  const handleReset = () => {
    resetCopilotSession();
    setMessages([
      {
        role: "assistant",
        content: "Conversation reset. How can I help you analyze your data?",
        response: {
          executive_summary: "Conversation reset. How can I help you analyze your data?",
          evidence: ["Session cleared"],
          confidence_score: 1.0,
          sql_used: null,
          datasets_used: [],
          tables_used: [],
          columns_used: [],
          kpis_used: [],
          business_reasoning: "Fresh session started.",
          follow_up_questions: SUGGESTED_QUESTIONS.slice(0, 3),
          charts: [],
          recommendation: { title: "Fresh Session", actions: [] },
          validation: { status: "IDLE", rows_returned: 0 },
          error: null,
          intent: "greeting",
          domain: "System",
          timestamp: new Date().toISOString(),
        },
      },
    ]);
    setActiveResponse(null);
    setConversationHistory([]);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const exportConversation = () => {
    const text = messages
      .map((m) => `[${m.role === "user" ? "YOU" : "COPILOT"}] ${m.content}`)
      .join("\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `copilot-conversation-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const togglePin = (idx: number) => {
    setPinnedResponses((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const retryLast = useCallback(() => {
    const lastUser = [...conversationHistory].reverse().find(t => t.role === "user");
    if (lastUser) {
      handleSend(lastUser.content);
    }
  }, [conversationHistory, handleSend]);

  const hasMessages = messages.length > 1 || (messages.length === 1 && messages[0].response?.intent !== "greeting");

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
      {/* Conversations sidebar */}
      <motion.div
        animate={{ width: sidebarOpen ? 256 : 0 }}
        transition={{ duration: 0.3 }}
        className="hidden lg:flex flex-col bg-surface border-r border-border-color overflow-hidden"
      >
        <div className="p-4 border-b border-border-light flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-bold text-text-primary uppercase tracking-wider">
            <History className="w-4 h-4 text-primary-600" />
            <span>Sessions</span>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="text-text-muted hover:text-text-secondary">
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>
        <div className="p-3">
          <button
            onClick={handleReset}
            className="w-full px-3 py-2 bg-primary-600 text-white text-xs font-semibold rounded-xl hover:bg-primary-700 transition shadow-sm flex items-center justify-center gap-2"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            New Session
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-3 space-y-1 text-xs">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`p-2.5 rounded-xl cursor-pointer border transition ${
                s.id === "current"
                  ? "bg-primary-50 dark:bg-primary-900/40 text-primary-700 dark:text-primary-200 font-semibold border-primary-200 dark:border-primary-700/50"
                  : "border-transparent hover:bg-surface-muted text-text-secondary"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="truncate flex-1">{s.title}</span>
                {s.pinned && <Pin className="w-3 h-3 text-warning-500 flex-shrink-0" />}
              </div>
              <span className="text-[10px] text-text-muted mt-0.5 block">
                {new Date(s.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          ))}
        </div>
      </motion.div>

      {!sidebarOpen && (
        <button
          onClick={() => setSidebarOpen(true)}
          className="hidden lg:block absolute left-2 top-20 z-20 bg-surface border border-border-color rounded-r-xl p-2 text-text-secondary hover:text-primary-600 shadow-sm"
        >
          <PanelLeftOpen className="w-4 h-4" />
        </button>
      )}

      {/* Chat column */}
      <div className="flex-1 flex flex-col min-w-0 bg-surface-muted">
        <div className="p-4 border-b border-border-color bg-surface flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-primary-50 text-primary-600 rounded-xl">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-base font-bold text-text-primary">Enterprise AI Copilot</h1>
              <p className="text-[11px] text-text-muted">Ask any business question about your data</p>
            </div>
            {activeResponse?.domain && (
              <span className="text-[11px] font-mono text-primary-700 dark:text-primary-300 bg-primary-50 dark:bg-primary-900/40 border border-primary-200 dark:border-primary-700/50 rounded-lg px-2 py-1 ml-2">
                {activeResponse.domain}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden md:flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-text-muted" />
              <select
                value={selectedWorkspaceId}
                onChange={async (e) => {
                  const val = e.target.value;
                  setSelectedWorkspaceId(val);
                  if (val && typeof window !== "undefined") {
                    localStorage.setItem("decisionlens_active_workspace", val);
                    window.dispatchEvent(new CustomEvent("decisionlens:workspace_changed", { detail: { workspace_id: val } }));
                    await api.post(`/workspaces/${val}/activate`).catch(() => null);
                  }
                }}
                className="text-xs font-semibold text-text-secondary bg-surface-muted border border-border-color rounded-lg px-2 py-1.5 outline-none focus:border-primary-600"
                aria-label="Select workspace"
              >
                <option value="">All Workspaces</option>
                {workspaces.map((ws) => (
                  <option key={ws.workspace_id} value={ws.workspace_id}>
                    {ws.name} {ws.industry ? `(${ws.industry})` : ""}
                  </option>
                ))}
              </select>
            </div>
            <div className="hidden md:flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-text-muted" />
              <select
                value={selectedDatasetId}
                onChange={(e) => setSelectedDatasetId(e.target.value)}
                className="text-xs font-semibold text-text-secondary bg-surface-muted border border-border-color rounded-lg px-2 py-1.5 outline-none focus:border-primary-600"
                aria-label="Select dataset"
              >
                <option value="">Auto-select</option>
                {datasets.map((ds) => (
                  <option key={ds.id} value={ds.id}>
                    {ds.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={() => setShowEvidencePanel(!showEvidencePanel)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-xl border transition-all ${
                showEvidencePanel
                  ? "bg-primary-50 text-primary-700 border-primary-200"
                  : "text-text-secondary border-border-color hover:bg-surface-muted"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5 inline mr-1" />
              Evidence
            </button>
            <button
              onClick={exportConversation}
              disabled={!hasMessages}
              className="px-3 py-1.5 text-xs font-semibold rounded-xl border border-border-color text-text-secondary hover:bg-surface-muted disabled:opacity-50 transition"
            >
              <Download className="w-3.5 h-3.5 inline mr-1" />
              Export
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <AnimatePresence>
            {messages.map((m, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <motion.div
                  className={`max-w-2xl rounded-2xl p-5 text-sm ${
                    m.role === "user"
                       ? "bg-gradient-to-br from-primary-600 to-primary-700 text-white shadow-lg shadow-primary-200 dark:shadow-primary-900/30"
                      : "bg-surface border border-border-color shadow-sm text-text-primary"
                  }`}
                  whileHover={{ scale: m.role === "user" ? 1 : 1.005 }}
                >
                  {/* Executive Summary Header */}
                  {m.role === "assistant" && m.response && (
                    <div className="mb-3 pb-3 border-b border-border-light flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-primary-600">
                          Executive Summary
                        </span>
                        {m.response.intent !== "error" && (
                          <span className="px-2 py-0.5 bg-success-100 text-success-700 text-[10px] font-bold rounded-full">
                            {Math.round((m.response.confidence_score || 0) * 100)}% Confidence
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => togglePin(idx)}
                          className={`p-1 rounded-lg transition-colors ${
                            pinnedResponses[idx]
                              ? "text-warning-500 bg-warning-50"
                              : "text-text-muted hover:text-text-secondary hover:bg-surface-muted"
                          }`}
                          aria-label={pinnedResponses[idx] ? "Unpin response" : "Pin response"}
                        >
                          <Pin className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  )}

                  <div className="leading-relaxed whitespace-pre-wrap">
                    {renderSimpleMarkdown(m.content)}
                  </div>

                  {/* Evidence & Metadata */}
                  {m.metadata && !m.response && (
                    <div className="mt-3 pt-3 border-t border-border-light flex items-center gap-3 text-[11px] text-text-muted">
                      <span className="font-mono text-primary-600">Intent: {m.metadata.intent}</span>
                      <span className="font-bold text-success-600">
                        Confidence: {Math.round((m.metadata.confidence || 0) * 100)}%
                      </span>
                    </div>
                  )}

                  {m.response && m.response.intent === "error" && (
                    <div className="mt-3 p-3 rounded-xl bg-error-500/10 dark:bg-error-900/40 border border-error-200 dark:border-error-700/50 text-xs space-y-2">
                      <div className="flex items-center gap-2 text-error-700 dark:text-error-300 font-semibold">
                        <AlertTriangle className="w-4 h-4" />
                        Analysis Unavailable
                      </div>
                      <p className="text-error-800 dark:text-error-200 leading-relaxed">
                        {m.response.executive_summary || m.content}
                      </p>
                      <button
                        onClick={retryLast}
                        disabled={loading}
                        className="mt-2 px-3 py-1.5 bg-error-600 hover:bg-error-700 disabled:bg-error-400 text-white dark:text-white text-xs font-semibold rounded-lg flex items-center gap-2 transition"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        Retry
                      </button>
                    </div>
                  )}

                  {m.response && m.response.intent !== "error" && (
                    <div className="mt-4 space-y-3">
                      {(m.response.kpis_used ?? []).length > 0 && (
                        <div className="p-3 rounded-xl bg-primary-50 dark:bg-primary-900/30 border border-primary-200 dark:border-primary-700/50 text-xs space-y-2">
                          <span className="text-[10px] font-bold text-primary-800 dark:text-primary-200 uppercase tracking-wider block">
                            Key Performance Indicators
                          </span>
                          <div className="flex flex-wrap gap-2">
                             {(m.response.kpis_used ?? []).map((kpi, i: number) => (
                               <span
                                 key={i}
                                 className="px-2.5 py-1 bg-primary-100 dark:bg-primary-800/40 border border-primary-200 dark:border-primary-700/50 rounded-lg text-[11px] font-bold text-primary-900 dark:text-primary-100"
                               >
                                 {getMetricDisplayValue(kpi)}
                               </span>
                             ))}
                          </div>
                        </div>
                      )}

                      {/* Business Impact */}
                      {m.response.business_reasoning && (
                        <div className="p-3 rounded-xl bg-warning-50 dark:bg-warning-900/30 border border-warning-200 dark:border-warning-700/50 text-xs space-y-1">
                          <span className="text-[10px] font-bold text-warning-800 dark:text-warning-200 uppercase tracking-wider block">
                            Business Impact
                          </span>
                          <p className="text-warning-800 dark:text-warning-200 leading-relaxed">{m.response.business_reasoning}</p>
                        </div>
                      )}

                      {/* Evidence Card */}
                      <CollapsibleCard
                        title="Evidence & Citations"
                        icon={<ShieldCheck className="w-3.5 h-3.5 text-success-600" />}
                        defaultOpen
                      >
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 bg-success-100 dark:bg-success-900/40 text-success-700 dark:text-success-300 text-[10px] font-bold rounded-full">
                              {Math.round((m.response.confidence_score || 0) * 100)}% Confidence
                            </span>
                            {m.response.sql_used && (
                              <span className="px-2 py-0.5 bg-surface-muted border border-border-color text-[10px] font-mono text-text-secondary rounded-full">
                                SQL-backed
                              </span>
                            )}
                          </div>
                          {(m.response.evidence ?? []).length > 0 && (
                            <div className="space-y-1.5">
                              {(m.response.evidence ?? []).map((ev: unknown, i: number) => (
                                <div key={i} className="flex items-start gap-2 text-text-secondary">
                                  <span className="text-success-600 mt-0.5">›</span>
                                  <span>{renderEvidenceValue(ev)}</span>
                                </div>
                              ))}
                            </div>
                          )}
                          {m.response.datasets_used?.length > 0 && (
                            <div className="text-[11px] text-text-muted pt-1 border-t border-border-light">
                              <span className="font-semibold">Sources:</span> {m.response.datasets_used.join(", ")}
                            </div>
                          )}
                        </div>
                      </CollapsibleCard>

                      {/* Recommendations */}
                      {m.response.recommendation && (
                        <div className="p-3 rounded-xl bg-success-50 dark:bg-success-900/30 border border-success-200 dark:border-success-700/50 text-xs space-y-2">
                          <div className="flex items-center gap-2">
                            <Target className="w-3.5 h-3.5 text-success-600" />
                            <span className="font-bold text-success-800 dark:text-success-200">
                              {m.response.recommendation?.title || "Executive Recommendation"}
                            </span>
                          </div>
                          {(Array.isArray(m.response.recommendation?.actions)
                            ? m.response.recommendation.actions
                            : []
                          ).length > 0 && (
                            <ul className="list-disc pl-4 text-success-800 dark:text-success-200 space-y-1">
                              {(Array.isArray(m.response.recommendation?.actions)
                                ? m.response.recommendation.actions
                                : []
                              ).map((a: string, i: number) => (
                                <li key={i}>{a}</li>
                              ))}
                            </ul>
                          )}
                          {(Array.isArray(m.response.recommendation?.risks) && m.response.recommendation.risks.length > 0) && (
                            <div className="pt-1.5 border-t border-success-200/60 dark:border-success-700/40">
                              <span className="text-[10px] font-bold text-error-700 dark:text-error-300 uppercase tracking-wider block mb-1">Risks</span>
                              <ul className="list-disc pl-4 text-error-700 dark:text-error-300 space-y-0.5">
                                {(m.response.recommendation?.risks as string[]).map((r: string, i: number) => (
                                  <li key={i}>{r}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {(Array.isArray(m.response.recommendation?.opportunities) && m.response.recommendation.opportunities.length > 0) && (
                            <div className="pt-1.5 border-t border-success-200/60 dark:border-success-700/40">
                              <span className="text-[10px] font-bold text-primary-700 dark:text-primary-300 uppercase tracking-wider block mb-1">Opportunities</span>
                              <ul className="list-disc pl-4 text-primary-700 dark:text-primary-300 space-y-0.5">
                                {(m.response.recommendation?.opportunities as string[]).map((o: string, i: number) => (
                                  <li key={i}>{o}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Next Actions / Follow-up */}
                      {(m.response.follow_up_questions ?? []).length > 0 && (
                        <div className="mt-2 pt-2 border-t border-border-light">
                          <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-2">
                            Suggested Follow-ups
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {(m.response.follow_up_questions ?? []).map((q, i) => (
                              <button
                                key={i}
                                onClick={() => handleSend(q)}
                                className="text-[11px] px-2.5 py-1.5 rounded-lg border border-primary-200 text-primary-700 hover:bg-primary-50 transition text-left"
                              >
                                {q}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Charts */}
                      {(m.response.charts ?? []).length > 0 && (
                        <div className="mt-2">
                          <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-2">
                            Available Visualizations
                          </p>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {(m.response.charts ?? [])
                              .filter((c: ChartItem | undefined) => c?.available)
                              .map((chart: ChartItem, i: number) => (
                                <ChartPreview key={i} chart={chart} />
                              ))}
                          </div>
                        </div>
                      )}

                      {/* Data Sources */}
                      <CollapsibleCard
                        title="Data Sources"
                        icon={<Database className="w-3.5 h-3.5 text-primary-600" />}
                      >
                        <div className="space-y-1">
                          <div>
                            <span className="text-text-muted">Datasets:</span>{" "}
                            <span className="font-mono text-text-primary">
                              {(m.response.datasets_used ?? []).join(", ") || "None"}
                            </span>
                          </div>
                          <div>
                            <span className="text-text-muted">Tables:</span>{" "}
                            <span className="font-mono text-text-primary">
                              {(m.response.tables_used ?? []).join(", ") || "None"}
                            </span>
                          </div>
                          <div>
                            <span className="text-text-muted">Columns:</span>{" "}
                            <span className="font-mono text-text-primary">
                              {(m.response.columns_used ?? []).join(", ") || "None"}
                            </span>
                          </div>
                        </div>
                      </CollapsibleCard>
                    </div>
                  )}
                </motion.div>
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-start"
            >
              <div className="bg-surface border border-border-color rounded-2xl shadow-sm overflow-hidden">
                <TypingIndicator />
                <div className="px-4 pb-3 text-xs text-text-primary dark:text-text-secondary flex items-center gap-2">
                  <Sparkles className="w-3.5 h-3.5 text-primary-600 animate-pulse" />
                  Analyzing your data and preparing executive insights...
                </div>
              </div>
            </motion.div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="p-4 bg-surface border-t border-border-color">
          <div className="flex items-center gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
               placeholder="Ask a business question (e.g. 'What is total revenue?')"
               rows={1}
               className="flex-1 px-4 py-3 text-sm border border-border-color rounded-xl outline-none focus:border-primary-600 bg-surface dark:bg-surface-elevated focus:bg-surface dark:focus:bg-surface-elevated transition resize-none"
               aria-label="Ask a business question"
            />
            <button
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              className="px-4 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-border-strong text-white dark:text-white text-sm font-semibold rounded-xl flex items-center gap-2 transition shadow-sm"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Ask
            </button>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {SUGGESTED_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => handleSend(q)}
                className="text-[11px] px-2.5 py-1.5 rounded-lg border border-border-color text-text-secondary hover:bg-primary-50 hover:text-primary-700 hover:border-primary-200 transition"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Evidence inspector panel */}
      {showEvidencePanel && activeResponse && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 384, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="hidden xl:flex flex-col bg-surface border-l border-border-color overflow-y-auto"
        >
          <div className="p-4 border-b border-border-light flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-text-primary uppercase tracking-wider">
              <ShieldCheck className="w-4 h-4 text-success-600" />
              <span>Evidence Inspector</span>
            </div>
            {activeResponse?.timestamp && (
              <span className="text-[10px] font-mono text-text-muted">
                {new Date(activeResponse.timestamp).toLocaleTimeString()}
              </span>
            )}
          </div>

          <div className="p-4 space-y-4 text-xs">
            <div className="p-3 rounded-xl bg-primary-50 border border-primary-100 space-y-1">
              <span className="text-[10px] font-bold text-primary-600 uppercase tracking-wider block">
                Executive Summary
              </span>
              <p className="text-text-secondary leading-relaxed">
                {activeResponse.executive_summary || "No executive summary available."}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-surface-muted border border-border-color space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">
                  Confidence Score
                </span>
                <span className="text-sm font-extrabold text-text-primary">
                  {Math.round((activeResponse.confidence_score || 0) * 100)}%
                </span>
              </div>
              <div className="flex-1 h-2 bg-surface-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-success-500 rounded-full transition-all"
                  style={{ width: `${(activeResponse.confidence_score || 0) * 100}%` }}
                />
              </div>
            </div>

            <div className="p-3 rounded-xl bg-surface-muted border border-border-color space-y-1">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">
                Evidence
              </span>
              <ul className="list-disc pl-4 space-y-1 text-text-secondary">
                {(activeResponse?.evidence ?? []).map((e, i) => (
                  <li key={i}>{renderEvidenceValue(e)}</li>
                ))}
              </ul>
            </div>

            <div className="p-3 rounded-xl bg-surface-muted border border-border-color space-y-1">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">
                Business Reasoning
              </span>
              <p className="text-text-secondary leading-relaxed">
                {activeResponse.business_reasoning || "Business reasoning is not available for this query."}
              </p>
            </div>

            <div className="p-3 rounded-xl bg-surface-muted border border-border-color space-y-1">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">
                Data Sources
              </span>
              <div className="space-y-1">
                <div>
                  <span className="text-text-muted">Datasets:</span>{" "}
                  <span className="font-mono text-text-primary">
                    {(activeResponse?.datasets_used ?? []).join(", ") || "None"}
                  </span>
                </div>
                <div>
                  <span className="text-text-muted">Tables:</span>{" "}
                  <span className="font-mono text-text-primary">
                    {(activeResponse?.tables_used ?? []).join(", ") || "None"}
                  </span>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-surface-muted border border-border-color space-y-1">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">
                Columns & KPIs
              </span>
              <div className="space-y-1">
                <div>
                  <span className="text-text-muted">Columns:</span>{" "}
                  <span className="font-mono text-text-primary">
                    {(activeResponse?.columns_used ?? []).join(", ") || "None"}
                  </span>
                </div>
                <div>
                  <span className="text-text-muted">KPIs:</span>{" "}
                  <span className="font-mono text-text-primary">
                     {(activeResponse?.kpis_used ?? []).map(getMetricDisplayValue).join(", ") || "None"}
                  </span>
                </div>
              </div>
            </div>

            {activeResponse.sql_used && (
              <div className="p-3 rounded-xl bg-background border border-border-color space-y-1">
                <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">
                  Analysis Method
                </span>
                <div className="relative">
                  <pre className="p-3 rounded-lg text-text-secondary font-mono text-[11px] overflow-x-auto whitespace-pre-wrap">
                    {activeResponse.sql_used}
                  </pre>
                  <button
                    onClick={() => copyToClipboard(activeResponse.sql_used || "")}
                    className="absolute top-2 right-2 text-text-muted hover:text-text-primary"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}

            {activeResponse.recommendation && (
              <div className="p-3 rounded-xl bg-success-50 dark:bg-success-900/30 border border-success-200 dark:border-success-700/50 space-y-1">
                <span className="text-[10px] font-bold text-success-800 dark:text-success-200 uppercase tracking-wider block">
                  Executive Recommendation
                </span>
                <p className="font-semibold text-text-primary mb-1">
                  {activeResponse.recommendation?.title || "Recommendation"}
                </p>
                <ul className="list-disc pl-4 space-y-1 text-success-800 dark:text-success-200">
                  {(Array.isArray(activeResponse.recommendation?.actions)
                    ? activeResponse.recommendation.actions
                    : []
                  ).map((a: string, i: number) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              </div>
            )}

            {activeResponse.validation && (
              <div className="p-3 rounded-xl bg-surface-muted border border-border-color space-y-1">
                <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">
                  Validation
                </span>
                <div className="space-y-1 text-text-secondary">
                  <div>
                    Status: <span className="font-semibold">{activeResponse.validation?.status || "UNKNOWN"}</span>
                  </div>
                  <div>
                    Rows Returned:{" "}
                    <span className="font-semibold">
                      {activeResponse.validation?.rows_returned?.toLocaleString() || 0}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {activeResponse.error && (
              <div className="p-3 rounded-xl bg-error-500/10 dark:bg-error-900/40 border border-error-200 dark:border-error-700/50 text-error-700 dark:text-error-300">
                <div className="flex items-center gap-2 font-semibold mb-1">
                  <AlertTriangle className="w-4 h-4" />
                  Error
                </div>
                <p className="leading-relaxed">{activeResponse.error}</p>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}
