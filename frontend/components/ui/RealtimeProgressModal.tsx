"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2,
  AlertCircle,
  Clock,
  RefreshCw,
  X,
  Sparkles,
  ArrowRight,
  Database,
  Layers,
  FileSpreadsheet
} from "lucide-react";

export interface ProgressStageItem {
  name: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  detail?: string;
}

export interface RealtimeProgressModalProps {
  isOpen: boolean;
  onClose?: () => void;
  title: string;
  subtitle?: string;
  percentage: number;
  currentStage: string;
  stages: ProgressStageItem[];
  status: "processing" | "completed" | "failed";
  errorMessage?: string;
  canCancel?: boolean;
  onCancel?: () => void;
  onDone?: () => void;
  doneButtonText?: string;
  stats?: {
    tables?: number;
    rows?: number;
    domain?: string;
    succeeded?: number;
    failed?: number;
  };
}

export default function RealtimeProgressModal({
  isOpen,
  onClose,
  title,
  subtitle,
  percentage,
  currentStage,
  stages,
  status,
  errorMessage,
  canCancel = false,
  onCancel,
  onDone,
  doneButtonText = "View Results",
  stats,
}: RealtimeProgressModalProps) {
  if (!isOpen) return null;

  const boundedPct = Math.min(100, Math.max(0, Math.round(percentage)));
  const isCompleted = status === "completed" || boundedPct >= 100;
  const isFailed = status === "failed";

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/70 backdrop-blur-md transition-opacity"
          onClick={() => {
            if (isCompleted || isFailed) onClose?.();
          }}
        />

        {/* Modal Window */}
        <motion.div
          initial={{ scale: 0.95, opacity: 0, y: 16 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 16 }}
          transition={{ type: "spring", duration: 0.35, bounce: 0.15 }}
          className="relative w-full max-w-lg rounded-3xl bg-surface border border-border-strong shadow-2xl overflow-hidden z-10 my-8"
        >
          {/* Top accent bar */}
          <div
            className={`h-1.5 w-full ${
              isFailed
                ? "bg-rose-500"
                : isCompleted
                ? "bg-gradient-to-r from-emerald-500 to-teal-400"
                : "bg-gradient-to-r from-primary-500 via-indigo-500 to-cyan-400 animate-pulse"
            }`}
          />

          <div className="p-6 sm:p-8 space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center ${
                      isFailed
                        ? "bg-rose-500/10 text-rose-500"
                        : isCompleted
                        ? "bg-emerald-500/10 text-emerald-500"
                        : "bg-primary-500/10 text-primary-500"
                    }`}
                  >
                    {isFailed ? (
                      <AlertCircle className="w-5 h-5" />
                    ) : isCompleted ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : (
                      <RefreshCw className="w-4 h-4 animate-spin text-primary-500" />
                    )}
                  </div>
                  <h3 className="text-lg font-bold text-text-primary tracking-tight">
                    {title}
                  </h3>
                </div>
                {subtitle && (
                  <p className="text-xs text-text-muted pl-10 leading-relaxed font-medium">
                    {subtitle}
                  </p>
                )}
              </div>

              {(isCompleted || isFailed) && onClose && (
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-xl p-1.5 text-text-muted hover:text-text-primary hover:bg-surface-muted transition-colors"
                  aria-label="Close modal"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Main Progress Bar & Counter */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-text-secondary flex items-center gap-1.5 truncate max-w-[75%]">
                  {!isCompleted && !isFailed && (
                    <span className="w-2 h-2 rounded-full bg-primary-500 animate-ping inline-block" />
                  )}
                  {isFailed ? "Processing Interrupted" : isCompleted ? "Completed Successfully" : currentStage}
                </span>
                <span className="font-mono font-bold text-text-primary">
                  {isFailed ? "Failed" : `${boundedPct}%`}
                </span>
              </div>

              <div className="w-full h-3 bg-surface-muted rounded-full overflow-hidden p-0.5 border border-border-color">
                <motion.div
                  className={`h-full rounded-full transition-all duration-300 ${
                    isFailed
                      ? "bg-rose-500"
                      : isCompleted
                      ? "bg-gradient-to-r from-emerald-500 to-teal-400"
                      : "bg-gradient-to-r from-primary-500 via-indigo-500 to-cyan-400"
                  }`}
                  style={{ width: `${boundedPct}%` }}
                />
              </div>
            </div>

            {/* Error Message Display if Failed */}
            {isFailed && errorMessage && (
              <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs space-y-1">
                <div className="font-bold flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>Pipeline Execution Error</span>
                </div>
                <p className="leading-relaxed pl-5 text-rose-400">{errorMessage}</p>
              </div>
            )}

            {/* Stages Checklist */}
            {stages && stages.length > 0 && (
              <div className="space-y-2 border border-border-color rounded-2xl p-4 bg-surface-muted/50 max-h-56 overflow-y-auto">
                <div className="text-[10px] font-bold uppercase tracking-wider text-text-muted mb-2">
                  Pipeline Execution Stages
                </div>
                {stages.map((st, idx) => {
                  const isDone = st.status === "completed";
                  const isCur = st.status === "in_progress";
                  const isErr = st.status === "failed";

                  return (
                    <div
                      key={idx}
                      className={`flex items-center justify-between p-2 rounded-xl text-xs transition-colors ${
                        isCur
                          ? "bg-primary-500/10 text-text-primary font-semibold border border-primary-500/20"
                          : "text-text-secondary"
                      }`}
                    >
                      <div className="flex items-center gap-2.5 truncate">
                        <div className="flex-shrink-0">
                          {isDone ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                          ) : isCur ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin text-primary-500" />
                          ) : isErr ? (
                            <AlertCircle className="w-4 h-4 text-rose-500" />
                          ) : (
                            <Clock className="w-3.5 h-3.5 text-text-muted" />
                          )}
                        </div>
                        <span className={`truncate ${isDone ? "text-text-muted line-through" : ""}`}>
                          {st.name}
                        </span>
                      </div>

                      <span className="text-[10px] font-mono capitalize ml-2 flex-shrink-0 text-text-muted">
                        {isDone ? "Done" : isCur ? "Active" : isErr ? "Failed" : "Pending"}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Stats Summary upon completion */}
            {isCompleted && stats && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-1">
                {stats.tables !== undefined && (
                  <div className="p-3 bg-surface-muted border border-border-color rounded-2xl text-center space-y-0.5">
                    <span className="text-[10px] font-bold text-text-muted uppercase block">Tables</span>
                    <strong className="text-base font-extrabold text-text-primary block">{stats.tables}</strong>
                  </div>
                )}
                {stats.rows !== undefined && (
                  <div className="p-3 bg-surface-muted border border-border-color rounded-2xl text-center space-y-0.5">
                    <span className="text-[10px] font-bold text-text-muted uppercase block">Records</span>
                    <strong className="text-base font-extrabold text-text-primary block">{stats.rows.toLocaleString()}</strong>
                  </div>
                )}
                {stats.domain && (
                  <div className="p-3 bg-surface-muted border border-border-color rounded-2xl text-center space-y-0.5">
                    <span className="text-[10px] font-bold text-text-muted uppercase block">Domain</span>
                    <strong className="text-base font-extrabold text-primary-500 block truncate">{stats.domain}</strong>
                  </div>
                )}
              </div>
            )}

            {/* Bottom Actions */}
            <div className="flex items-center justify-end gap-3 pt-2">
              {!isCompleted && !isFailed && canCancel && onCancel && (
                <button
                  type="button"
                  onClick={onCancel}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold text-text-muted hover:text-text-primary hover:bg-surface-muted transition-colors border border-border-color"
                >
                  Cancel
                </button>
              )}

              {isFailed && onClose && (
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-surface-muted text-text-primary hover:bg-surface border border-border-color transition-colors"
                >
                  Dismiss
                </button>
              )}

              {isCompleted && onDone && (
                <button
                  type="button"
                  onClick={onDone}
                  className="w-full sm:w-auto px-6 py-2.5 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-500 hover:to-indigo-500 shadow-md shadow-primary-500/20 flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
                >
                  <span>{doneButtonText}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
