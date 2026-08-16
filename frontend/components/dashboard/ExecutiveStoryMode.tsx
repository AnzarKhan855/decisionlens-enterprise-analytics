"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { BookOpen, Sparkles, HelpCircle, CheckCircle2 } from "lucide-react";
import InsightExplanationModal, { InsightDetail } from "./InsightExplanationModal";

export default function ExecutiveStoryMode({ storyText }: { storyText?: string }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [activeInsight, setActiveInsight] = useState<InsightDetail | null>(null);

  if (!storyText) {
    return null;
  }

  function openExplanation() {
    setActiveInsight({
      title: "Executive Story Mode Narrative",
      why_important: "Converts database rows and multi-table schemas into plain-English executive prose for CEOs and non-technical business leaders.",
      how_calculated: "RAG synthesis engine summarizing record totals, gross revenue sums, and metric distributions.",
      recommended_action: "Review operational recommendations in Decision Center.",
      business_impact: "Provides instant executive operational clarity."
    });
    setModalOpen(true);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="premium-card text-text-primary rounded-2xl p-7 border border-border-color shadow-lg space-y-4"
    >
      <InsightExplanationModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        insight={activeInsight}
      />

      <div className="flex items-center justify-between border-b border-foreground/10 pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-primary-500/20 text-primary-300 rounded-2xl border border-primary-500/30">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-extrabold text-text-primary">Executive Business Story</h3>
            <span className="text-[11px] text-text-muted">Plain-English AI Synthesis</span>
          </div>
        </div>

        <button
          onClick={openExplanation}
          className="px-3 py-1.5 bg-surface/10 hover:bg-surface/20 text-text-secondary rounded-xl text-xs font-bold border border-foreground/10 flex items-center gap-1.5 transition-colors focus-visible:ring-2 focus-visible:ring-primary-400"
          aria-label="Explain Executive Business Story narrative"
        >
          <HelpCircle className="w-3.5 h-3.5 text-primary-300" />
          <span>Explain Narrative</span>
        </button>
      </div>

      <p className="text-sm text-text-secondary leading-relaxed font-medium">
        {storyText}
      </p>
    </motion.div>
  );
}
