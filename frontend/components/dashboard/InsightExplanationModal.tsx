"use client";

import React from "react";
import { motion } from "framer-motion";
import { Sparkles, HelpCircle, Calculator, Target, X, CheckCircle2 } from "lucide-react";

export interface InsightDetail {
  title: string;
  why_important: string;
  how_calculated: string;
  recommended_action: string;
  business_impact?: string;
}

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  insight: InsightDetail | null;
}

export default function InsightExplanationModal({ isOpen, onClose, insight }: ModalProps) {
  if (!isOpen || !insight) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/60 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className="bg-surface border border-border-color rounded-2xl shadow-2xl max-w-lg w-full p-6 lg:p-7 space-y-6 relative overflow-hidden"
      >
        {/* Ambient Top Glow */}
        <div className="absolute top-0 right-0 w-48 h-48 bg-primary-500/10 rounded-full blur-3xl -z-10" />

        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-border-light pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-primary-50 text-primary-600 rounded-xl border border-primary-100">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold uppercase tracking-widest text-primary-600">
                Executive Copilot Explanation
              </span>
              <h3 className="text-lg font-bold text-text-primary leading-snug">{insight.title}</h3>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-text-muted hover:text-text-primary hover:bg-surface-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body: 3 Executive Questions */}
        <div className="space-y-4 text-xs">
          {/* Question 1: Why is this important? */}
          <div className="p-4 bg-primary-50/60 border border-primary-100 rounded-2xl space-y-1.5">
            <div className="flex items-center gap-2 font-bold text-primary-800 text-sm">
              <HelpCircle className="w-4 h-4 text-primary-600" />
              <span>1. Why is this important?</span>
            </div>
            <p className="text-text-primary leading-relaxed font-medium">
              {insight.why_important}
            </p>
          </div>

          {/* Question 2: How was this calculated? */}
          <div className="p-4 bg-surface-muted border border-border-color rounded-2xl space-y-1.5">
            <div className="flex items-center gap-2 font-bold text-text-primary text-sm">
              <Calculator className="w-4 h-4 text-text-secondary" />
              <span>2. How was this calculated?</span>
            </div>
            <p className="text-text-secondary leading-relaxed font-mono text-[11px]">
              {insight.how_calculated}
            </p>
          </div>

          {/* Question 3: What business action should I take? */}
          <div className="p-4 bg-success-50/70 border border-success-200 rounded-2xl space-y-1.5">
            <div className="flex items-center gap-2 font-bold text-emerald-950 text-sm">
              <Target className="w-4 h-4 text-success-600" />
              <span>3. What business action should I take?</span>
            </div>
            <p className="text-success-800 leading-relaxed font-semibold">
              {insight.recommended_action}
            </p>
            {insight.business_impact && (
              <div className="mt-2 pt-2 border-t border-success-200 text-[11px] font-bold text-success-700">
                Estimated ROI / Business Impact: {insight.business_impact}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="pt-2 border-t border-border-light flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2.5 bg-primary-600 hover:bg-primary-700 text-white text-xs font-semibold rounded-xl transition-all shadow-md shadow-primary-600/30 flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4" />
            Understood
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
