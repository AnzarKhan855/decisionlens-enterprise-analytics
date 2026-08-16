"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { FolderPlus, FileArchive, Upload, Sparkles, CheckCircle2, AlertCircle, RefreshCw, Layers, Database, ArrowRight, Building2 } from "lucide-react";

import { activateAndSyncWorkspace } from "@/lib/workspace-resolver";
import { invalidateCache } from "@/lib/api";
import { uploadZipWorkspace, uploadFolderWorkspace } from "@/lib/upload";
import { API_BASE_URL } from "@/lib/api";

export default function WorkspaceUploadWizard() {
  const [activeTab, setActiveTab] = useState<"zip" | "folder">("zip");
  const [workspaceName, setWorkspaceName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [stageIndex, setStageIndex] = useState<number>(0);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const PROGRESS_STAGES = [
    "Reading files...",
    "Detecting relationships...",
    "Building business model...",
    "Finding revenue, customers, products, time series...",
    "Checking data quality...",
    "Building semantic model...",
    "Generating executive insights..."
  ];

  async function simulateProgressAndSubmit(uploadFn: () => Promise<any>) {
    setUploading(true);
    setError(null);
    setResult(null);
    setStageIndex(0);

    let stageTimer: any;
    try {
      stageTimer = setInterval(() => {
        setStageIndex((prev) => (prev < PROGRESS_STAGES.length - 1 ? prev + 1 : prev));
      }, 400);

      const resData = await uploadFn();
      setResult(resData);
      activateAndSyncWorkspace(resData);
      invalidateCache();

      if (typeof window !== "undefined") {
        setTimeout(() => {
          window.location.href = "/dynamic-dashboard";
        }, 300);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "An error occurred during workspace ingestion.";
      if (err.response?.status === 401) {
        setError("Session expired or authentication required. Please log in again to upload datasets.");
      } else {
        setError(msg);
      }
    } finally {
      clearInterval(stageTimer);
      setUploading(false);
    }
  }

  async function handleZipUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    await simulateProgressAndSubmit(async () => {
      return await uploadZipWorkspace(file, workspaceName);
    });
  }

  async function handleFolderUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    await simulateProgressAndSubmit(async () => {
      return await uploadFolderWorkspace(files, workspaceName);
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
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeTab === "zip" ? "bg-surface text-primary-600 shadow-sm" : "text-text-secondary hover:text-text-primary"
            }`}
          >
            ZIP Archive (.zip)
          </button>
          <button
            onClick={() => setActiveTab("folder")}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeTab === "folder" ? "bg-surface text-primary-600 shadow-sm" : "text-text-secondary hover:text-text-primary"
            }`}
          >
            Project Folder
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <label className="block text-xs font-bold text-text-primary uppercase tracking-wider">Workspace Identifier</label>
        <input
          type="text"
          value={workspaceName}
          onChange={(e) => setWorkspaceName(e.target.value)}
          placeholder="e.g. Enterprise Business Workspace"
          className="w-full px-4 py-3 bg-surface-muted border border-border-color rounded-2xl text-sm font-semibold text-text-primary focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Upload Box Area */}
      <div className="border-2 border-dashed border-border-color rounded-2xl p-8 bg-primary-50/30 text-center hover:border-primary-300 hover:bg-primary-50/50 transition-all cursor-pointer relative premium-card">
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

      {/* Live AI Progress Stepper */}
      <AnimatePresence>
        {uploading && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
             className="premium-card p-6 space-y-4 overflow-hidden"
          >
            <div className="flex items-center justify-between border-b border-border-color pb-3">
              <div className="flex items-center gap-3">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
                >
                  <RefreshCw className="w-5 h-5 text-primary-400" />
                </motion.div>
                <h3 className="text-sm font-extrabold text-text-primary">Analyzing Your Business...</h3>
              </div>
              <span className="text-xs font-mono text-primary-300">Estimated time: 30–60 seconds</span>
            </div>

            <div className="space-y-2">
              {PROGRESS_STAGES.map((st, idx) => {
                const isDone = idx < stageIndex;
                const isCurrent = idx === stageIndex;
                return (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="flex items-center gap-3 text-xs"
                  >
                    {isDone ? (
                      <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 400 }}>
                        <CheckCircle2 className="w-4 h-4 text-success-400 flex-shrink-0" />
                      </motion.div>
                    ) : isCurrent ? (
                      <motion.div
                        animate={{ opacity: [0.4, 1, 0.4] }}
                        transition={{ repeat: Infinity, duration: 1.4 }}
                      >
                        <RefreshCw className="w-4 h-4 text-primary-400 flex-shrink-0" />
                      </motion.div>
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-border-color flex-shrink-0" />
                    )}
                    <span className={isDone ? "text-text-muted font-medium" : isCurrent ? "text-primary-300 font-bold" : "text-text-secondary"}>
                      {st}
                    </span>
                  </motion.div>
                );
              })}
            </div>
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
             className="premium-card p-4 flex items-center gap-3 text-error-800 text-xs font-semibold"
          >
            <AlertCircle className="w-4 h-4 text-error-600 flex-shrink-0" />
            <span>{error}</span>
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
             className="premium-card p-7 space-y-5"
          >
            <div className="flex items-center justify-between border-b border-border-color pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-success-500/20 text-success-300 rounded-2xl border border-success-500/30">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-success-400 block font-bold">Analysis Complete</span>
                  <h3 className="text-lg font-extrabold text-text-primary">Executive Briefing & Workspace Overview</h3>
                </div>
              </div>
              <span className="px-3 py-1 bg-primary-500/20 text-primary-300 text-xs font-extrabold rounded-full border border-primary-500/30">
                {result.total_tables_ingested || 8} Tables Analyzed
              </span>
            </div>

            <p className="text-xs text-text-muted leading-relaxed font-medium">
              Your dataset has been analyzed successfully.
            </p>

            <div className="space-y-2 pt-1">
              <strong className="text-xs text-primary-400 block uppercase font-bold tracking-wider">DecisionLens Can Answer Automatically:</strong>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-semibold text-text-secondary">
                {["Revenue trends", "Customer behavior", "Seller performance", "Delivery performance", "Product performance", "Forecasting", "Customer churn", "Regional performance"].map((item) => (
                  <div key={item} className="p-2.5 bg-surface/5 rounded-xl border border-foreground/10 flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-success-400" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 flex items-center justify-end">
              <Link
                href="/dynamic-dashboard"
                className="inline-flex items-center gap-2 px-7 py-3.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-extrabold rounded-2xl shadow-lg shadow-primary-600/30 transition-all"
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
