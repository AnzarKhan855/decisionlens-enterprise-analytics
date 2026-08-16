"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Activity, Bell, CheckCircle2, AlertTriangle, Sparkles, HelpCircle } from "lucide-react";
import InsightExplanationModal, { InsightDetail } from "./InsightExplanationModal";

interface NewsItem {
  time: string;
  title: string;
  impact: string;
  body: string;
}

export default function ExecutiveNewsfeed({ news }: { news?: NewsItem[] }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [activeInsight, setActiveInsight] = useState<InsightDetail | null>(null);

  if (!news || news.length === 0) {
    return null;
  }
  const items = news;

  function openExplanation(item: NewsItem) {
    setActiveInsight({
      title: `Newsfeed Alert: ${item.title}`,
      why_important: item.body,
      how_calculated: `Automated statistical scan over daily business transaction records.`,
      recommended_action: item.impact === "Risk" ? "Review logistics carrier contracts." : "Capitalize on high-performing category momentum.",
      business_impact: `Operational Alert (${item.time})`
    });
    setModalOpen(true);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="premium-card rounded-2xl p-7 border border-border-color shadow-sm space-y-6"
    >
      <InsightExplanationModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        insight={activeInsight}
      />

      <div className="flex items-center justify-between border-b border-border-light pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600 mb-1">
            <Activity className="w-4 h-4 text-primary-600" /> AI Business Coach Newsfeed
          </div>
          <h2 className="text-xl font-extrabold text-text-primary">Real-Time Company News &amp; Operational Alerts</h2>
        </div>

        <span className="text-xs font-mono text-text-muted bg-surface-muted px-3.5 py-1.5 rounded-full border border-border-color">
          Continuous Scan Active
        </span>
      </div>

      <ul className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 list-none p-0 m-0" aria-label="News feed items">
        {items.map((n, idx) => {
          const isRisk = n.impact === "Risk";
          return (
            <motion.li
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.06, duration: 0.35 }}
              whileHover={{ y: -3, transition: { duration: 0.2 } }}
              className={`premium-card p-5 rounded-2xl border flex flex-col justify-between space-y-3 transition-all hover:shadow-md ${
                isRisk ? "bg-warning-50/70 border-warning-200" : "bg-surface-muted border-border-color"
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold font-mono text-primary-600 uppercase">{n.time}</span>
                  <span
                    className={`px-2 py-0.5 text-[10px] font-extrabold rounded-md uppercase ${
                      isRisk ? "bg-warning-200 text-warning-800" : "bg-success-100 text-success-800"
                    }`}
                  >
                    {n.impact}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-text-primary leading-snug">{n.title}</h3>
                <p className="text-xs text-text-secondary leading-relaxed">{n.body}</p>
              </div>

              <div className="pt-2 border-t border-border-color flex justify-end">
                <button
                  onClick={() => openExplanation(n)}
                  className="p-1 bg-surface hover:bg-border-color rounded-lg text-text-secondary text-[11px] font-bold border border-border-color flex items-center gap-1 transition-colors focus-visible:ring-2 focus-visible:ring-primary-500"
                  aria-label={`Explain ${n.title}`}
                >
                  <HelpCircle className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
                  <span>Explain</span>
                </button>
              </div>
            </motion.li>
          );
        })}
      </ul>
    </motion.div>
  );
}
