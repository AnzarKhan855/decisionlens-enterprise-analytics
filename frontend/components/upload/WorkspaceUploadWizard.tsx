"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  FolderPlus, FileArchive, Upload, Sparkles, CheckCircle2,
  AlertCircle, RefreshCw, Layers, Database, ArrowRight, Building2, Clock, XCircle
} from "lucide-react";

import { activateAndSyncWorkspace } from "@/lib/workspace-resolver";
import { invalidateCache } from "@/lib/api";
import {
  uploadZipWorkspace, uploadFolderWorkspace,
  getWorkspaceProcessingStatus
} from "@/lib/upload";

export default function WorkspaceUploadWizard() {
  const [activeTab, setActiveTab] = useState<"zip" | "folder">("zip");
  const [workspaceName, setWorkspaceName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [processingProgress, setProcessingProgress] = useState<number>(0);
  const [currentStepText, setCurrentStepText] = useState<string>("Uploading files...");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [stepsList, setStepsList] = useState<Array<{ step: string; status: string }>>([]);

  const startTimeRef = useRef<number>(0);
  const timerRef = useRef<any>(null);
  const pollRef = useRef<any>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  async function startPipelineTracking(workspaceId: string, initialData: any) {
    setCurrentStepText("Ingesting tables and profiling schemas...");
    setProcessingProgress(25);

    pollRef.current = setInterval(async () => {
      try {
        const stData = await getWorkspaceProcessingStatus(workspaceId);
        if (stData) {
          if (stData.progress !== undefined) {
            setProcessingProgress(stData.progress);
          }
          if (stData.current_step) {
            setCurrentStepText(stData.current_step);
          } else if (stData.message) {
            setCurrentStepText(stData.message);
          }
          if (stData.steps && Array.isArray(stData.steps)) {
            setStepsList(stData.steps);
          }

          if (stData.status === "COMPLETED" || stData.status === "SEMANTIC_READY" || stData.is_ready) {
            clearInterval(pollRef.current);
            clearInterval(timerRef.current);
            setProcessingProgress(100);
            setCurrentStepText("AI Executive Insights Fully Prepared");
            setResult(initialData);
            activateAndSyncWorkspace(initialData);
            invalidateCache();
            setUploading(false);
          } else if (stData.status === "FAILED") {
            clearInterval(pollRef.current);
            clearInterval(timerRef.current);
            setUploading(false);
            setError(stData.error?.message || "Workspace ingestion failed.");
          }
        }
      } catch (pollErr) {
        console.warn("[WorkspaceUploadWizard] Status poll warning:", pollErr);
      }
    }, 1000);
  }

  async function handleUploadExecution(
    uploadFn: (onProgress: (pct: number) => void) => Promise<any>
  ) {
    setUploading(true);
    setError(null);
    setResult(null);
    setUploadProgress(0);
    setProcessingProgress(5);
    setCurrentStepText("Streaming dataset to server...");
    setElapsedSeconds(0);

    startTimeRef.current = Date.now();
    timerRef.current = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);

    try {
      const resData = await uploadFn((pct) => {
        setUploadProgress(pct);
        if (pct < 100) {
          setCurrentStepText(`Uploading archive (${pct}%)...`);
        }
      });

      setUploadProgress(100);
      const wsId = resData.workspace_id || resData.active_workspace;

      if (wsId) {
        await startPipelineTracking(wsId, resData);
      } else {
        // Instant synchronous success
        clearInterval(timerRef.current);
        setResult(resData);
        activateAndSyncWorkspace(resData);
        invalidateCache();
        setUploading(false);
      }
    } catch (err: any) {
      clearInterval(timerRef.current);
      if (pollRef.current) clearInterval(pollRef.current);
      setUploading(false);
      const msg = err.response?.data?.detail || err.response?.data?.message || err.message || "An error occurred during workspace ingestion.";
      if (err.response?.status === 401) {
        setError("Session expired or authentication required. Please log in again to upload datasets.");
      } else {
        setError(msg);
      }
    }
  }

  async function handleZipUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    await handleUploadExecution(async (onProgress) => {
      return await uploadZipWorkspace(file, workspaceName, onProgress);
    });
  }

  async function handleFolderUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    await handleUploadExecution(async (onProgress) => {
      return await uploadFolderWorkspace(files, workspaceName, onProgress);
    });
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="premium-card p-8 space-y-6 max-w-4xl mx-auto"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-light pb-4">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-primary-600">Enterprise Multi-Table Ingestion</span>
          <h2 className="text-2xl font-extrabold text-text-primary mt-0.5 flex items-center gap-2">
            <Layers className="w-6 h-6 text-primary-600" />
            Upload Business Workspace
          </h2>
        </div>

        <div className="flex items-center gap-2 bg-surface-muted p-1 rounded-xl border border-border-color">
          <button
            onClick={() => setActiveTab("zip")}
            disabled={uploading}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeTab === "zip" ? "bg-surface text-primary-600 shadow-sm" : "text-text-secondary hover:text-text-primary"
            }`}
          >
            ZIP Archive (.zip)
          </button>
          <button
            onClick={() => setActiveTab("folder")}
            disabled={uploading}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeTab === "folder" ? "bg-surface text-primary-600 shadow-sm" : "text-text-secondary hover:text-text-primary"
            }`}
          >
            Project Folder
          </button>
        </div>
      </div>

      <div className="space-y-2">
        <label className="block text-xs font-bold text-text-primary uppercase tracking-wider">Workspace Identifier</label>
        <input
          type="text"
          value={workspaceName}
          onChange={(e) => setWorkspaceName(e.target.value)}
          disabled={uploading}
          placeholder="e.g. Enterprise Business Workspace"
          className="w-full px-4 py-3 bg-surface-muted border border-border-color rounded-2xl text-sm font-semibold text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
        />
      </div>

      {/* Upload Box Area */}
      <div className={`border-2 border-dashed border-border-color rounded-2xl p-8 bg-primary-50/30 text-center transition-all relative premium-card ${
        uploading ? "opacity-60 cursor-not-allowed" : "hover:border-primary-300 hover:bg-primary-50/50 cursor-pointer"
      }`}>
        {activeTab === "zip" ? (
          <div className="space-y-3">
            <FileArchive className="w-12 h-12 text-primary-600 mx-auto" />
            <div>
              <h3 className="text-base font-extrabold text-text-primary">Upload Enterprise ZIP Archive</h3>
              <p className="text-xs text-text-muted mt-1">Upload a ZIP containing Orders, Customers, Products, Reviews, and Payments</p>
            </div>
            <input
              type="file"
              accept=".zip"
              onChange={handleZipUpload}
              disabled={uploading}
              className="absolute inset-0 opacity-0 cursor-pointer"
            />
          </div>
        ) : (
          <div className="space-y-3">
            <FolderPlus className="w-12 h-12 text-primary-600 mx-auto" />
            <div>
              <h3 className="text-base font-extrabold text-text-primary">Upload Entire Project Folder</h3>
              <p className="text-xs text-text-muted mt-1">Select or drag & drop an entire directory of related CSV/Excel files</p>
            </div>
            <input
              type="file"
              // @ts-ignore
              webkitdirectory=""
              directory=""
              multiple
              onChange={handleFolderUpload}
              disabled={uploading}
              className="absolute inset-0 opacity-0 cursor-pointer"
            />
          </div>
        )}
      </div>

      {/* Live Asynchronous Progress Stepper */}
      <AnimatePresence>
        {uploading && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="premium-card p-6 space-y-4 overflow-hidden border border-border-color"
          >
            <div className="flex items-center justify-between border-b border-border-color pb-3">
              <div className="flex items-center gap-3">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
                >
                  <RefreshCw className="w-5 h-5 text-primary-500" />
                </motion.div>
                <div>
                  <h3 className="text-sm font-extrabold text-text-primary">
                    {uploadProgress !== null && uploadProgress < 100
                      ? "Streaming Workspace to Server..."
                      : "Analyzing Enterprise Workspace..."}
                  </h3>
                  <p className="text-xs text-text-muted mt-0.5">{currentStepText}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono text-text-secondary bg-surface-muted px-2.5 py-1 rounded-lg border border-border-color">
                <Clock className="w-3.5 h-3.5 text-primary-500" />
                <span>{elapsedSeconds}s</span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="space-y-1.5">
              <div className="w-full bg-surface-muted rounded-full h-2.5 overflow-hidden border border-border-color">
                <motion.div
                  className="bg-primary-600 h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${
                      uploadProgress !== null && uploadProgress < 100
                        ? uploadProgress
                        : Math.max(processingProgress, 20)
                    }%`,
                  }}
                />
              </div>
              <div className="flex justify-between text-[11px] font-mono text-text-muted">
                <span>Memory-safe ingestion pipeline</span>
                <span>
                  {uploadProgress !== null && uploadProgress < 100
                    ? `${uploadProgress}% network upload`
                    : `${Math.round(processingProgress)}% processed`}
                </span>
              </div>
            </div>

            {/* Discovered or Active Steps */}
            {stepsList.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-border-light">
                {stepsList.map((st, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-xs">
                    {st.status === "COMPLETED" ? (
                      <CheckCircle2 className="w-4 h-4 text-success-500 flex-shrink-0" />
                    ) : st.status === "PROCESSING" ? (
                      <RefreshCw className="w-4 h-4 text-primary-500 animate-spin flex-shrink-0" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-border-color flex-shrink-0" />
                    )}
                    <span className={st.status === "COMPLETED" ? "text-text-muted line-through" : st.status === "PROCESSING" ? "text-primary-600 font-bold" : "text-text-secondary"}>
                      {st.step}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="p-4 bg-error-50 text-error-800 rounded-2xl border border-error-200 text-xs flex items-start gap-3"
          >
            <AlertCircle className="w-4 h-4 text-error-600 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-bold block">Ingestion Notice</span>
              <span className="leading-relaxed">{error}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Post-Analysis Executive Briefing */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.5 }}
            className="premium-card p-7 space-y-5 border border-success-200 bg-success-50/20"
          >
            <div className="flex items-center justify-between border-b border-border-color pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-success-100 text-success-700 rounded-2xl border border-success-200">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-success-600 block font-bold">Analysis Complete</span>
                  <h3 className="text-lg font-extrabold text-text-primary">Executive Briefing & Workspace Overview</h3>
                </div>
              </div>
              <span className="px-3 py-1 bg-primary-100 text-primary-700 text-xs font-extrabold rounded-full border border-primary-200">
                {result.total_tables_ingested || result.datasets_count || 1} Table(s) Ingested
              </span>
            </div>

            <p className="text-xs text-text-secondary leading-relaxed font-medium">
              Your business workspace <strong>{result.workspace_name || result.workspace_id}</strong> has been structured, relational schemas mapped, and AI intelligence prepared.
            </p>

            <div className="space-y-2 pt-1">
              <strong className="text-xs text-primary-600 block uppercase font-bold tracking-wider">DecisionLens Can Answer Automatically:</strong>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-semibold text-text-secondary">
                {["Revenue trends", "Customer behavior", "Seller performance", "Delivery performance", "Product performance", "Forecasting", "Customer churn", "Regional performance"].map((item) => (
                  <div key={item} className="p-2.5 bg-surface rounded-xl border border-border-color flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-success-500" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 flex items-center justify-end">
              <Link
                href="/dynamic-dashboard"
                className="inline-flex items-center gap-2 px-7 py-3.5 bg-primary-600 hover:bg-primary-700 text-white text-xs font-extrabold rounded-2xl shadow-lg shadow-primary-600/30 transition-all"
              >
                <span>Launch Dashboard</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
