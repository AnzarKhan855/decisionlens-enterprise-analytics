"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Zap, CheckCircle2, TrendingUp, HelpCircle, ArrowRight, ShieldCheck, Clock, User, DollarSign } from "lucide-react";
import InsightExplanationModal, { InsightDetail } from "./InsightExplanationModal";

interface ActionItem {
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

const PRIORITY_STYLES: Record<string, { label: string; cls: string }> = {
  High:   { label: "P1", cls: "bg-error-100 text-error-800 border-error-300" },
  Medium: { label: "P2", cls: "bg-warning-100 text-warning-800 border-warning-300" },
  Low:    { label: "P3", cls: "bg-info-100 text-info-800 border-info-300" },
  Critical: { label: "P0", cls: "bg-error-100 text-error-800 border-error-300" },
};

function resolvePriority(priority: string) {
  const normalized = priority.toLowerCase();
  if (normalized.includes("high") || normalized.includes("critical")) return PRIORITY_STYLES.High;
  if (normalized.includes("medium")) return PRIORITY_STYLES.Medium;
  if (normalized.includes("low")) return PRIORITY_STYLES.Low;
  if (normalized.includes("critical")) return PRIORITY_STYLES.Critical;
  return { label: priority, cls: "bg-surface-muted text-text-primary border-border-strong" };
}

export default function ExecutiveActionCenter({ actions }: { actions?: ActionItem[] }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [activeInsight, setActiveInsight] = useState<InsightDetail | null>(null);

  if (!actions || actions.length === 0) {
    return null;
  }
  const items = actions;

  function openExplanation(item: ActionItem) {
    setActiveInsight({
      title: item.action,
      why_important: item.explanation,
      how_calculated: `analytics query: ${item.evidence_sql}`,
      recommended_action: `Execute this ${item.priority.toLowerCase()} initiative owned by ${item.owner} within ${item.time}.`,
      business_impact: `Expected Financial Outcome: ${item.expected_roi}`
    });
    setModalOpen(true);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="premium-card p-6 lg:p-7 space-y-6"
    >
      <InsightExplanationModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        insight={activeInsight}
      />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600 mb-1">
            <Zap className="w-4 h-4 text-warning-500 fill-warning-500" /> Executive Action Center
          </div>
          <h2 className="text-xl font-extrabold text-text-primary">Top Strategic Decisions To Execute Today</h2>
        </div>

        <span className="text-xs font-mono text-text-muted bg-surface-muted px-3.5 py-1.5 rounded-full border border-border-color self-start sm:self-auto">
          Prioritized by Financial Impact ($)
        </span>
      </div>

      <ul className="grid grid-cols-1 md:grid-cols-2 gap-6 list-none p-0 m-0" aria-label="Strategic action items">
        {items.map((item) => {
          const style = resolvePriority(item.priority);
          return (
            <motion.li
              key={item.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35 }}
              whileHover={{ y: -3, transition: { duration: 0.2 } }}
              className="premium-card p-5 flex flex-col justify-between space-y-4 shadow-sm"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span
                    className={`px-2.5 py-1 text-[11px] font-extrabold rounded-full border uppercase tracking-wide flex items-center gap-1.5 ${style.cls}`}
                  >
                    <span className="w-4 h-4 rounded-full bg-surface/30 flex items-center justify-center text-[9px] font-black">{style.label}</span>
                    {item.priority}
                  </span>

                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-success-600 font-extrabold bg-success-50 px-2.5 py-0.5 rounded-full border border-success-200">
                      {item.confidence} Confidence
                    </span>
                    <button
                      onClick={() => openExplanation(item)}
                      className="p-1 bg-surface hover:bg-border-color rounded-lg text-text-secondary text-[11px] font-bold border border-border-color flex items-center gap-1 transition-colors focus-visible:ring-2 focus-visible:ring-primary-500"
                      aria-label={`Explain ${item.action}`}
                    >
                      <HelpCircle className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
                      <span>Explain</span>
                    </button>
                  </div>
                </div>

              <h3 className="text-lg font-extrabold text-text-primary leading-snug">{item.action}</h3>
              <p className="text-xs text-text-secondary leading-relaxed">{item.explanation}</p>
            </div>

            <div className="pt-4 border-t border-border-color/80 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5 text-success-700 font-extrabold text-sm">
                  <DollarSign className="w-4 h-4 text-success-600" />
                  <span>Expected ROI: {item.expected_roi}</span>
                </div>
                <div className="flex items-center gap-1 text-text-muted font-mono text-[11px]">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{item.time}</span>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-text-muted pt-1">
                <span>Owner: <strong className="text-text-primary font-semibold">{item.owner}</strong></span>
                <span>Difficulty: <strong className="text-text-primary font-semibold">{item.difficulty}</strong></span>
              </div>
            </div>
            </motion.li>
          );
        })}
      </ul>
    </motion.div>
  );
}
