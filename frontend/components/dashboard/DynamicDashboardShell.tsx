"use client";

import React, { useEffect, useState, useMemo, useCallback, Suspense, lazy } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import ForecastChartRenderer from "@/components/charts/ForecastChartRenderer";
import InsightExplanationModal, { InsightDetail } from "./InsightExplanationModal";
import GuidedOnboardingModal from "./GuidedOnboardingModal";
import DynamicSectionRenderer from "./DynamicSectionRenderer";
import api from "@/lib/api";
import { getDynamicDashboard } from "@/lib/dynamic-dashboard";
import type { DashboardPayload, MetricObject, PredictionItem } from "@/lib/types";
import {
  Activity, AlertTriangle, CheckCircle2,
  Building2, FolderArchive, Upload,
  Layers, ArrowRight, Zap,
  MessageCircleQuestion,
  FileText, MessageSquare, BarChart3,
  RefreshCw,
} from "lucide-react";

const AIAssistantChat = lazy(() => import("./AIAssistantChat"));
const WhatIfSimulator = lazy(() => import("./WhatIfSimulator"));
const ExecutiveActionCenter = lazy(() => import("./ExecutiveActionCenter"));
const ExecutiveStoryMode = lazy(() => import("./ExecutiveStoryMode"));
const ExecutiveNewsfeed = lazy(() => import("./ExecutiveNewsfeed"));
const MultiAgentExecutiveView = lazy(() => import("./MultiAgentExecutiveView"));

const LoadingStagesComponent = React.memo(function LoadingStagesComponent({ loadingStages, loadingStage, progress }: { loadingStages: string[]; loadingStage: number; progress: number }) {
  return (
    <div className="flex flex-col items-center gap-6 max-w-sm w-full px-6">
      <motion.div
         className="w-10 h-10 border-2 border-primary-600 border-t-transparent rounded-full"
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 0.9, ease: "linear" }}
      />
      <div className="w-full space-y-3 text-center">
        <p className="text-sm font-bold text-text-primary">{loadingStages[loadingStage] || "Loading your dashboard..."}</p>
        <div className="w-full bg-border-color rounded-full h-2 overflow-hidden">
          <motion.div
            className="bg-primary-600 h-full rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
        <p className="text-[10px] text-text-muted font-medium">{Math.round(progress)}% complete</p>
        <div className="flex flex-col gap-1.5 pt-1">
          {loadingStages.map((stage, i) => {
            const done = i < loadingStage;
            const current = i === loadingStage;
            return (
              <div key={i} className="flex items-center gap-2 text-[10px] font-medium text-left">
                {done ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-success-500 flex-shrink-0" />
                ) : current ? (
                  <motion.div
                    className="w-3.5 h-3.5 rounded-full border-2 border-primary-500 flex-shrink-0"
                    animate={{ opacity: [0.4, 1, 0.4] }}
                    transition={{ repeat: Infinity, duration: 1.4 }}
                  />
                ) : (
                  <div className="w-3.5 h-3.5 rounded-full border border-border-strong flex-shrink-0" />
                )}
                <span className={done ? "text-text-muted" : current ? "text-primary-600 font-bold" : "text-text-muted"}>{stage}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
});

const ErrorDisplay = React.memo(function ErrorDisplay({ error, dashboard, onRetry }: { error: string | null; dashboard: DashboardPayload | null; onRetry: () => void }) {
  const errorMessage = typeof error === "string" ? error : (error as unknown as { message?: string })?.message || "Failed to load dashboard payload.";
  const hasWorkspace = dashboard?.workspace_exists !== false;
  const diagnostics = (dashboard?.error_details as { detail?: string; workspace_id?: string; status?: string; step?: string } | null) || null;
  return (
    <motion.div
      className="p-8 flex items-center justify-center min-h-[70vh]"
      role="alert"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
       <div className="bg-surface rounded-2xl p-10 border border-border-color shadow-lg text-center flex flex-col items-center justify-center space-y-6 max-w-xl w-full">
        <div className="p-5 bg-primary-50 text-primary-600 rounded-2xl border border-primary-100">
          <FolderArchive className="w-14 h-14 text-primary-600" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-extrabold text-text-primary">{hasWorkspace ? "Dashboard Unavailable" : "No Workspaces Yet"}</h2>
          <p className="text-xs text-text-muted leading-relaxed max-w-md">{errorMessage}</p>
          {diagnostics && (
            <div className="text-left bg-surface-muted rounded-2xl p-4 border border-border-color text-[11px] text-text-secondary font-mono space-y-1 max-w-md">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">Diagnostics</span>
              {diagnostics.detail && <div><strong>Detail:</strong> {diagnostics.detail}</div>}
              {diagnostics.workspace_id && <div><strong>Workspace:</strong> {diagnostics.workspace_id}</div>}
              {diagnostics.status && <div><strong>Status:</strong> {diagnostics.status}</div>}
              {diagnostics.step && <div><strong>Step:</strong> {diagnostics.step}</div>}
            </div>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onRetry}
            className="px-6 py-3.5 bg-primary-600 hover:bg-primary-500 text-white font-extrabold text-xs rounded-2xl transition-all shadow-lg shadow-primary-600/30 flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Retry</span>
          </button>
          <Link href="/upload" className="px-6 py-3.5 bg-background hover:bg-surface-muted text-text-primary font-extrabold text-xs rounded-2xl transition-all shadow-lg flex items-center gap-2">
            <Upload className="w-4 h-4" />
            <span>Upload Dataset</span>
          </Link>
        </div>
      </div>
    </motion.div>
  );
});

const LookupWarning = React.memo(function LookupWarning({ dashboard }: { dashboard: DashboardPayload }) {
  const warning = (dashboard.lookup_table_warning as { title?: string; message?: string; required_datasets?: string[] }) || {};
  return (
    <div className="p-8 flex items-center justify-center min-h-[70vh]" role="alert">
       <div className="bg-surface rounded-2xl p-10 border border-border-color shadow-lg text-center flex flex-col items-center justify-center space-y-6 max-w-2xl w-full">
        <div className="p-5 bg-warning-50 text-warning-600 rounded-2xl border border-warning-100 shadow-inner"><AlertTriangle className="w-14 h-14 text-warning-600" /></div>
        <div className="space-y-3">
          <span className="px-3 py-1 bg-warning-100 text-warning-800 text-xs font-extrabold rounded-full uppercase tracking-wider">Reference / Lookup Dataset</span>
          <h2 className="text-2xl font-extrabold text-text-primary">{warning.title || "Reference / Lookup Data Uploaded"}</h2>
          <p className="text-xs text-text-secondary leading-relaxed font-medium max-w-xl">{warning.message || "The uploaded file is a reference lookup table containing category translations/mappings. It does not contain operational or transactional business metrics."}</p>
        </div>
          {warning.required_datasets && (
            <div className="w-full bg-surface-muted p-4 rounded-2xl border border-border-color text-left space-y-2">
              <span className="text-xs font-bold text-text-primary block uppercase tracking-wide">Required Additional Datasets for Executive Analytics:</span>
              <ul className="list-disc pl-5 text-xs text-text-secondary space-y-1 font-medium">
                {(warning.required_datasets || []).map((req: string, i: number) => (
                  <li key={i}>{req}</li>
                ))}
              </ul>
            </div>
          )}
        <div className="flex items-center gap-3 pt-2">
          <Link href="/upload" className="px-6 py-3.5 bg-primary-600 hover:bg-primary-500 text-white font-extrabold text-xs rounded-xl transition-all shadow-lg shadow-primary-600/30 flex items-center gap-2"><Upload className="w-4 h-4" /><span>Upload Transactional Dataset</span></Link>
          <Link href="/workspace-structure" className="px-5 py-3.5 bg-surface-muted hover:bg-border-color text-text-secondary font-bold text-xs rounded-xl transition-all flex items-center gap-2"><Layers className="w-4 h-4 text-text-muted" /><span>View Workspace Structure</span></Link>
        </div>
      </div>
    </div>
  );
});

const NoKpisState = React.memo(function NoKpisState() {
  return (
    <div className="p-8 flex items-center justify-center min-h-[70vh]" role="alert">
      <div className="bg-surface rounded-2xl p-10 border border-border-color shadow-sm text-center flex flex-col items-center justify-center space-y-6 max-w-xl w-full">
        <div className="p-4 bg-info-50 text-info-600 rounded-2xl border border-info-100"><FolderArchive className="w-12 h-12 text-info-600" /></div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-text-primary">No measurable business data detected</h2>
          <p className="text-xs text-text-muted leading-relaxed max-w-md">Your dataset needs numeric measure columns (such as revenue, quantity, or amount) and date or category columns to generate executive KPIs and intelligent visualizations.</p>
        </div>
        <Link href="/upload" className="px-6 py-3.5 bg-primary-600 hover:bg-primary-500 text-white font-extrabold text-xs rounded-xl transition-all shadow-lg shadow-primary-600/30 flex items-center gap-2"><Upload className="w-4 h-4" /><span>Upload Business Dataset</span></Link>
      </div>
    </div>
  );
});

export default function DynamicDashboardShell() {
  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingStage, setLoadingStage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [activeInsight] = useState<InsightDetail | null>(null);
  const [onboardingOpen, setOnboardingOpen] = useState(false);
  const [bgStatus, setBgStatus] = useState<{ status: string; current_step?: string; progress: number } | null>(null);

  const loadingStages = useMemo(() => [
    "Connecting to data warehouse...",
    "Understanding your dataset...",
    "Building semantic model...",
    "Generating analytics...",
    "Building dashboard...",
    "Preparing executive report...",
  ], []);

  const doLoad = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setLoadingStage(0);
      let activeWsId = typeof window !== "undefined"
        ? localStorage.getItem("decisionlens_active_workspace")
        : null;

      if (!activeWsId) {
        setLoadingStage(1);
        const res = await api.get("/workspace/active").catch(() => null);
        const foundId = res?.data?.workspace?.workspace_id || res?.data?.workspace_id;
        if (foundId) {
          activeWsId = foundId;
          localStorage.setItem("decisionlens_active_workspace", foundId);
          localStorage.setItem("decisionlens_user_workspace", foundId);
        }
      }

      setLoadingStage(2);
      const data = await getDynamicDashboard(activeWsId || undefined);
      setLoadingStage(3);
      setDashboard(data);
      setLoadingStage(4);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard payload.");
    } finally {
      setLoading(false);
      setLoadingStage(5);
    }
  }, []);

  useEffect(() => {
    (async () => {
      await doLoad();
    })();
    let intervalId: ReturnType<typeof setInterval> | null = null;
    async function pollStatus() {
      try {
        const wsRes = await api.get("/workspaces");
        const wsData = wsRes.data;
        const activeId = wsData.active_workspace_id;
        if (!activeId) return;
        const stRes = await api.get(`/workspace/${activeId}/status`);
        const stData = stRes.data;
        setBgStatus(stData as { status: string; current_step?: string; progress: number });
        if (stData.status === "COMPLETED" || stData.status === "SEMANTIC_READY") {
          if (intervalId) clearInterval(intervalId);
        }
      } catch (e) {
        console.warn("[Dashboard] Background status poll failed", e);
      }
    }
    pollStatus();
    intervalId = setInterval(pollStatus, 2000);
    return () => { if (intervalId) clearInterval(intervalId); };
  }, [doLoad]);

  const handleRetry = useCallback(() => {
    setError(null);
    setLoading(true);
    setLoadingStage(0);
    doLoad();
  }, [doLoad]);

  if (loading) {
    const progress = Math.min(100, ((loadingStage + 1) / loadingStages.length) * 100);
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <LoadingStagesComponent loadingStages={loadingStages} loadingStage={loadingStage} progress={progress} />
      </div>
    );
  }

  if (error || !dashboard) {
    return <ErrorDisplay error={error} dashboard={dashboard} onRetry={handleRetry} />;
  }

  if (dashboard.is_lookup_only) {
    return <LookupWarning dashboard={dashboard} />;
  }

  if (!dashboard.kpis || dashboard.kpis.length === 0) {
    return <NoKpisState />;
}

  const briefing = dashboard.executive_briefing || { greeting: "Executive Briefing", business_name: "Active Workspace", health_score: dashboard.health_score || 0, primary_metric: "N/A", status: "Ready", main_opportunity: "Empirical optimization active", biggest_risk: "Monitor operational risks", forecast: "Predictive model active", ai_confidence: "N/A" };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto"
    >
      <InsightExplanationModal isOpen={modalOpen} onClose={() => setModalOpen(false)} insight={activeInsight} />
      <GuidedOnboardingModal isOpen={onboardingOpen} onClose={() => setOnboardingOpen(false)} dashboardData={dashboard} />

      {/* Background Processing Banner */}
      <AnimatePresence>
        {bgStatus && bgStatus.status === "PROCESSING" && (
          <motion.div
            className="bg-gradient-to-r from-primary-600 via-primary-50 to-primary-600 dark:from-primary-800 dark:via-background dark:to-primary-800 border border-primary-500/40 rounded-2xl p-5 text-text-primary dark:text-white shadow-md flex flex-col md:flex-row items-center justify-between gap-4"
            role="status"
            aria-label="Processing your data"
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.4 }}
          >
            <div className="flex items-center gap-4">
              <div className="p-3 bg-primary-500/20 rounded-xl border border-primary-400/30 flex items-center justify-center">
                <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ repeat: Infinity, duration: 1.2 }}>
                  <Zap className="w-5 h-5 text-primary-400" />
                </motion.div>
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 bg-success-500/20 text-success-300 font-black text-[10px] uppercase tracking-wider rounded-full border border-success-500/30 flex items-center gap-1"><CheckCircle2 className="w-3 h-3 text-success-400" />Workspace Ready</span>
                  <span className="text-xs text-primary-400 font-bold">AI is analyzing your data</span>
                </div>
                <h4 className="text-sm font-extrabold text-text-primary">{bgStatus.current_step || "Preparing Executive Insights..."} ({bgStatus.progress}%)</h4>
              </div>
            </div>
            <div className="w-full md:w-56 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-text-muted"><span>Progress</span><span className="text-primary-400">{bgStatus.progress}%</span></div>
              <div className="w-full bg-surface-muted rounded-full h-2 overflow-hidden border border-border-color">
                <motion.div
                  className="bg-gradient-to-r from-primary-500 to-success-400 h-full rounded-full"
                  animate={{ width: `${bgStatus.progress}%` }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ==================== EXECUTIVE BRIEFING HERO ==================== */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="relative bg-gradient-to-br from-surface via-primary-50 to-surface dark:from-background dark:via-primary-800 dark:to-background text-text-primary dark:text-white rounded-2xl shadow-lg border border-border-color overflow-hidden"
      >
        {/* Glass overlay pattern */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(99,102,241,0.12)_0%,transparent_60%)]" aria-hidden="true" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(16,185,129,0.06)_0%,transparent_60%)]" aria-hidden="true" />
        <div className="relative p-8 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-foreground/10 pb-6">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <span className="px-3 py-1 bg-primary-500/20 text-primary-300 font-extrabold text-xs rounded-full border border-primary-500/30 uppercase tracking-wide">{briefing.business_name}</span>
                <span className="px-3 py-1 bg-success-500/20 text-success-300 font-extrabold text-xs rounded-full border border-success-500/30 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5 text-success-400" />Health: {briefing.health_score} / 100</span>
              </div>
              <h1 className="text-3xl lg:text-4xl font-extrabold tracking-tight text-text-primary mt-3">{briefing.greeting}</h1>
              <p className="text-xs text-text-muted mt-2 max-w-2xl leading-relaxed font-medium">Executive briefing generated from your uploaded workspace. All indicators are verified against your data.</p>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={() => setOnboardingOpen(true)} className="px-5 py-3 bg-surface/10 hover:bg-surface/20 text-text-primary text-xs font-bold rounded-2xl transition-all border border-foreground/10 flex items-center gap-2"><Building2 className="w-4 h-4 text-success-400" /><span>Executive Walkthrough</span></button>
              <Link href="/reports" className="px-6 py-3 bg-primary-600 hover:bg-primary-500 text-white text-xs font-extrabold rounded-2xl transition-all shadow-lg shadow-primary-600/30 flex items-center gap-2"><span>Board Reports</span><ArrowRight className="w-4 h-4" /></Link>
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 text-xs" role="list" aria-label="Executive indicators">
            {(dashboard.kpis && dashboard.kpis.length > 0
              ? dashboard.kpis.filter((k: MetricObject) => k.available !== false).slice(0, 5)
              : [{ name: "Dataset Domain", formatted_value: dashboard.intelligence?.domain || dashboard.dataset_type || "Generic", value: dashboard.intelligence?.domain || dashboard.dataset_type || "Generic", confidence: 0 }, { name: "Health Score", formatted_value: `${dashboard.health_score || 95}/100`, value: dashboard.health_score || 95, confidence: 0 }, { name: "Total Records", formatted_value: `${dashboard.profile?.total_rows || 0}`, value: dashboard.profile?.total_rows || 0, confidence: 0 }]
            ).map((k: { name: string; formatted_value: string; value: string | number }, i: number) => (
              <div key={i} className="p-4 bg-surface/5 rounded-2xl border border-foreground/10" role="listitem">
                <span className="text-text-muted text-[11px] font-bold block uppercase tracking-wider">{k.name}</span>
                <strong className="text-success-400 text-xl font-extrabold block mt-0.5 truncate">{k.formatted_value || String(k.value)}</strong>
              </div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* ==================== DYNAMIC SECTIONS ==================== */}
      <DynamicSectionRenderer sections={dashboard.sections || []} />

      {/* ==================== MULTI-AGENT ADVISORY ==================== */}
      <Suspense fallback={<div className="p-8 text-center text-xs text-text-muted font-bold animate-pulse">Loading Multi-Agent Advisory...</div>}>
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.45 }}
        >
          <MultiAgentExecutiveView reports={dashboard.multi_agent_reports} />
        </motion.div>
      </Suspense>
      <Suspense fallback={<div className="p-8 text-center text-xs text-text-muted font-bold animate-pulse">Loading Executive Story...</div>}>
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.45 }}
        >
          <ExecutiveStoryMode storyText={dashboard.executive_story} />
        </motion.div>
      </Suspense>

      {/* ==================== WHAT SHOULD EXECUTIVES DO ==================== */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] }}
           className="bg-surface rounded-2xl p-7 border border-border-color shadow-sm space-y-5"
      >
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600">
          <Zap className="w-4 h-4 text-warning-500 fill-warning-500" />
          <span>What Should Executives Do</span>
        </div>
          <h2 className="text-xl font-extrabold text-text-primary">Recommended Actions</h2>
          <p className="text-sm text-text-muted leading-relaxed max-w-3xl">
          Prioritized by expected business impact. Each action includes evidence, confidence level, and implementation guidance.
        </p>
        <ExecutiveActionCenter actions={dashboard.action_center} />
      </motion.section>

      {/* ==================== SCENARIO SIMULATOR ==================== */}
      <Suspense fallback={<div className="p-8 text-center text-xs text-text-muted font-bold animate-pulse">Loading Scenario Simulator...</div>}>
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45, duration: 0.45 }}
        >
          <WhatIfSimulator />
        </motion.div>
      </Suspense>

      {/* ==================== PREDICTION CHARTS ==================== */}
      {dashboard.predictions && dashboard.predictions.length > 0 && (
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] }}
           className="bg-surface rounded-2xl p-7 border border-border-color shadow-sm space-y-5"
        >
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600">
            <Activity className="w-4 h-4" />
            <span>Forecast Visualizations</span>
          </div>
          <h2 className="text-xl font-extrabold text-text-primary">Predicted Trends</h2>
          <p className="text-sm text-text-muted leading-relaxed max-w-3xl">AI-powered time-series forecasts based on your historical business data. Confidence intervals shown where available.
          </p>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {dashboard.predictions.slice(0, 2).map((pred: PredictionItem, idx: number) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 + idx * 0.1, duration: 0.4 }}
                  className="bg-surface-muted rounded-2xl p-5 border border-border-color"
                >
                  <ForecastChartRenderer data={pred} />
                </motion.div>
              ))}
          </div>
        </motion.section>
      )}

      {/* ==================== AI BUSINESS QUESTIONS ==================== */}
      {dashboard.intelligence?.business_questions && dashboard.intelligence.business_questions.length > 0 && (
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.55, duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="bg-surface rounded-2xl p-7 border border-border-color shadow-sm space-y-4"
        >
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600">
            <MessageCircleQuestion className="w-4 h-4" />
            <span>Ask About Your Business</span>
          </div>
          <h2 className="text-xl font-extrabold text-text-primary">Suggested Questions</h2>
          <p className="text-sm text-text-muted leading-relaxed max-w-3xl">
            Questions tailored to your {dashboard.intelligence.domain} dataset by the AI analysis system.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            {dashboard.intelligence.business_questions.map((q: string, idx: number) => (
              <button
                key={idx}
                type="button"
                className="p-4 bg-primary-50/50 hover:bg-primary-100/60 border border-primary-200 hover:border-primary-300 rounded-2xl cursor-pointer transition-all flex items-center justify-between group text-left w-full"
              >
                <span className="font-semibold text-primary-800 group-hover:text-primary-900">{q}</span>
                <ArrowRight className="w-4 h-4 text-primary-400 group-hover:text-primary-600 transition-transform group-hover:translate-x-0.5" />
              </button>
            ))}
          </div>
        </motion.section>
      )}

      {/* ==================== NEXT STEPS ==================== */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] }}
         className="bg-surface rounded-2xl p-7 border border-border-color shadow-lg text-text-primary space-y-4"
      >
        <h2 className="text-lg font-extrabold text-text-primary">Next Steps</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <Link href="/dynamic-dashboard" className="p-4 bg-surface/5 hover:bg-surface/10 rounded-2xl border border-foreground/10 transition-all flex items-center gap-3">
            <BarChart3 className="w-5 h-5 text-primary-400" />
            <div>
               <span className="block font-bold text-text-primary">Explore Full Dashboard</span>
               <span className="text-xs text-text-muted">Deep dive into all metrics and charts</span>
            </div>
          </Link>
          <Link href="/copilot" className="p-4 bg-surface/5 hover:bg-surface/10 rounded-2xl border border-foreground/10 transition-all flex items-center gap-3">
            <MessageSquare className="w-5 h-5 text-success-400" />
            <div>
               <span className="block font-bold text-text-primary">Ask AI Copilot</span>
               <span className="text-xs text-text-muted">Get answers to specific business questions</span>
            </div>
          </Link>
          <Link href="/reports" className="p-4 bg-surface/5 hover:bg-surface/10 rounded-2xl border border-foreground/10 transition-all flex items-center gap-3">
            <FileText className="w-5 h-5 text-warning-400" />
            <div>
               <span className="block font-bold text-text-primary">View Board Report</span>
               <span className="text-xs text-text-muted">Presentation-ready executive report</span>
            </div>
          </Link>
        </div>
      </motion.section>

      {/* ==================== TIMELINE & NEWS ==================== */}
      <Suspense fallback={<div className="p-8 text-center text-xs text-text-muted font-bold animate-pulse">Loading Executive Newsfeed...</div>}>
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.65, duration: 0.45 }}
        >
          <ExecutiveNewsfeed news={dashboard.executive_newsfeed} />
        </motion.div>
      </Suspense>
      <Suspense fallback={<div className="p-8 text-center text-xs text-text-muted font-bold animate-pulse">Loading AI Assistant...</div>}>
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.45 }}
        >
          <AIAssistantChat datasetId={dashboard.dataset_id} />
        </motion.div>
      </Suspense>

      {/* Technical Details Toggle */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.75 }}
        className="text-center"
      >
        <button
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
          className="px-4 py-2 text-[11px] font-semibold text-text-muted hover:text-text-secondary border border-border-color rounded-xl transition-colors"
        >
          {showTechnicalDetails ? "Hide" : "Show"} Technical Details
        </button>
      </motion.div>
    </motion.div>
  );
}
