"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Info, Sparkles, Building2, HelpCircle, FileSpreadsheet, Layers, ShieldCheck, ChevronDown, ChevronUp } from "lucide-react";

interface DatasetOverviewBannerProps {
  datasetType?: string;
  datasetName?: string;
  rowCount?: number;
  colCount?: number;
  profile?: any;
}

export default function DatasetOverviewBanner({
  datasetType = "Generic Dataset",
  datasetName = "uploaded_dataset",
  rowCount = 0,
  colCount = 0,
  profile
}: DatasetOverviewBannerProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="bg-gradient-to-br from-primary-800 via-background to-background text-text-primary dark:text-white rounded-2xl p-6 border border-primary-800/40 shadow-lg space-y-4"
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-foreground/10 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary-500/20 text-primary-400 rounded-xl border border-primary-500/30">
            <Building2 className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-extrabold uppercase tracking-widest bg-primary-500/20 text-primary-300 px-2.5 py-0.5 rounded-full border border-primary-500/30">
                Executive Plain-English Overview
              </span>
              <span className="text-xs text-text-muted">{datasetType}</span>
            </div>
            <h2 className="text-xl font-bold text-text-primary mt-1">
              Dataset Profile: {datasetName}
            </h2>
          </div>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="px-3.5 py-1.5 bg-surface/10 hover:bg-surface/15 text-text-secondary text-xs font-semibold rounded-xl border border-foreground/10 flex items-center gap-2 transition-all"
        >
          <span>{expanded ? "Collapse Overview" : "Expand Plain-English Overview"}</span>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {expanded && (
        <div className="space-y-4 text-xs text-text-muted leading-relaxed pt-1">
          <p className="bg-surface-muted/50 p-4 rounded-xl border border-border-color text-text-secondary">
            <strong>What this dataset represents: </strong>
            This is a <strong>{datasetType}</strong> dataset containing {rowCount.toLocaleString()} records across {colCount} columns. It has been profiled, validated, and prepared for AI-powered analytics and decision intelligence.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-surface-muted/50 rounded-xl border border-border-color space-y-1">
               <span className="text-primary-400 font-bold uppercase tracking-wider text-[10px] flex items-center gap-1">
                 <FileSpreadsheet className="w-3.5 h-3.5" /> Total Records & Attributes
               </span>
               <div className="text-base font-extrabold text-text-primary">
                 {rowCount.toLocaleString()} Rows × {colCount} Columns
               </div>
              <p className="text-[11px] text-text-muted">Validated data structure with quality scoring.</p>
            </div>

            <div className="p-4 bg-surface-muted/50 rounded-xl border border-border-color space-y-1">
               <span className="text-success-400 font-bold uppercase tracking-wider text-[10px] flex items-center gap-1">
                 <ShieldCheck className="w-3.5 h-3.5" /> Analysis Readiness
               </span>
               <div className="text-xs font-bold text-text-primary">
                 Trend Analysis, Root Causes, Forecasting
               </div>
              <p className="text-[11px] text-text-muted">Automated statistical and ML-powered insights enabled.</p>
            </div>

            <div className="p-4 bg-surface-muted/50 rounded-xl border border-border-color space-y-1">
               <span className="text-primary-400 font-bold uppercase tracking-wider text-[10px] flex items-center gap-1">
                 <Sparkles className="w-3.5 h-3.5" /> AI Consultant Capability
               </span>
               <div className="text-xs font-bold text-text-primary">
                 Evidence-Based Strategic Guidance
               </div>
              <p className="text-[11px] text-text-muted">Generates prioritized actions with confidence scoring.</p>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
