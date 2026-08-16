"use client";

import React from "react";
import { motion } from "framer-motion";
import { Users, ShieldCheck, TrendingUp, DollarSign, Truck, Sparkles, Award } from "lucide-react";

export interface AgentReport {
  agent: string;
  focus: string;
  finding: string;
  recommendation: string;
  impact: string;
  confidence: string;
}

export default function MultiAgentExecutiveView({ reports }: { reports?: AgentReport[] }) {
  if (!reports || reports.length === 0) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="premium-card rounded-2xl p-7 border border-border-color shadow-sm space-y-6"
    >
      <div className="flex items-center justify-between border-b border-border-light pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-primary-50 text-primary-600 rounded-2xl border border-primary-200">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-extrabold text-text-primary flex items-center gap-2">
              <span>Multi-Agent Executive Advisory System</span>
              <span className="px-2.5 py-0.5 bg-primary-100 text-primary-800 font-extrabold text-[10px] rounded-full uppercase tracking-wide">
                7 AI C-Suite Agents
              </span>
            </h3>
            <p className="text-xs text-text-muted font-medium">
              Autonomous C-Suite agents analyzing workspace facts to deliver consensus recommendations.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {reports.map((report, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.07, duration: 0.35 }}
            whileHover={{ y: -3, transition: { duration: 0.2 } }}
            className="premium-card p-5 rounded-2xl border border-border-color/80 hover:border-primary-300 transition-all flex flex-col justify-between space-y-4 shadow-sm"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-extrabold text-primary-700 uppercase tracking-wide bg-primary-50 px-2.5 py-0.5 rounded-md border border-primary-100">
                  {report.agent.split("(")[0]}
                </span>
                <span className="text-[10px] font-extrabold text-success-700 bg-success-50 px-2 py-0.5 rounded border border-success-100 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-success-600" />
                  {report.confidence} Confidence
                </span>
              </div>

              <strong className="text-xs font-extrabold text-text-primary block leading-snug">
                {report.focus}
              </strong>

              <p className="text-[11px] text-text-secondary leading-relaxed font-medium">
                {report.finding}
              </p>

              <div className="p-3 bg-surface rounded-xl border border-border-color/60 space-y-1">
                <span className="text-[10px] font-extrabold text-primary-800 uppercase block">Recommendation</span>
                <p className="text-[11px] text-text-primary font-semibold leading-relaxed">
                  {report.recommendation}
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-border-color/60 flex items-center justify-between">
              <span className="text-[10px] text-text-muted font-bold uppercase">Expected Impact</span>
              <strong className="text-xs font-extrabold text-success-700 flex items-center gap-1">
                <TrendingUp className="w-3.5 h-3.5 text-success-600" />
                {report.impact}
              </strong>
            </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    );
  }
