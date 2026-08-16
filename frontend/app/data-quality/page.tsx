"use client";

import React from "react";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Database,
  FileCheck,
  Activity,
  Sparkles,
  RefreshCw,
  Sliders,
  HelpCircle
} from "lucide-react";

export default function DataTrustPage() {
  return (
    <div className="p-8 space-y-8">
          {/* Header Banner */}
          <div className="bg-background text-text-primary p-8 rounded-2xl shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-6 border border-border-color premium-card">
            <div>
              <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-widest text-success-400 mb-1">
                <ShieldCheck className="w-4 h-4" /> Data Trust Scorecard
              </div>
              <h1 className="text-3xl font-extrabold tracking-tight">Can I Trust My Data?</h1>
              <p className="text-sm text-text-muted max-w-2xl mt-1 leading-relaxed">
                DecisionLens continuously verifies missing records, duplicates, broken links, and unusual data spikes in plain English before generating executive dashboards.
              </p>
            </div>

            <div className="flex items-center gap-3 bg-success-500/20 px-5 py-3.5 rounded-2xl border border-success-500/30">
              <div>
                <span className="text-[10px] font-extrabold uppercase tracking-wider text-success-300 block">Overall Trust Score</span>
                <strong className="text-3xl font-extrabold text-text-primary">98 / 100</strong>
              </div>
            </div>
          </div>

          {/* Trust Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-surface p-6 rounded-2xl border border-border-color shadow-sm space-y-2 premium-card">
              <div className="flex items-center justify-between text-text-muted">
                <span className="text-xs font-semibold uppercase tracking-wider">Duplicate Records</span>
                <CheckCircle2 className="w-4 h-4 text-success-600" />
              </div>
              <h3 className="text-2xl font-extrabold text-text-primary">0 Duplicates</h3>
              <p className="text-xs text-success-600 font-semibold">Clean Unique Records</p>
            </div>

            <div className="bg-surface p-6 rounded-2xl border border-border-color shadow-sm space-y-2 premium-card">
              <div className="flex items-center justify-between text-text-muted">
                <span className="text-xs font-semibold uppercase tracking-wider">Missing Values</span>
                <CheckCircle2 className="w-4 h-4 text-success-600" />
              </div>
              <h3 className="text-2xl font-extrabold text-text-primary">&lt;0.01% Nulls</h3>
              <p className="text-xs text-success-600 font-semibold">No Missing Fields</p>
            </div>

            <div className="bg-surface p-6 rounded-2xl border border-border-color shadow-sm space-y-2 premium-card">
              <div className="flex items-center justify-between text-text-muted">
                <span className="text-xs font-semibold uppercase tracking-wider">Broken Links</span>
                <ShieldCheck className="w-4 h-4 text-primary-600" />
              </div>
              <h3 className="text-2xl font-extrabold text-text-primary">0 Broken Links</h3>
              <p className="text-xs text-primary-600 font-semibold">All Table Keys Match</p>
            </div>

            <div className="bg-surface p-6 rounded-2xl border border-border-color shadow-sm space-y-2 premium-card">
              <div className="flex items-center justify-between text-text-muted">
                <span className="text-xs font-semibold uppercase tracking-wider">Data Spikes</span>
                <AlertTriangle className="w-4 h-4 text-warning-500" />
              </div>
              <h3 className="text-2xl font-extrabold text-text-primary">1 Unusual Spike</h3>
              <p className="text-xs text-warning-600 font-semibold">Flagged for Verification</p>
            </div>
          </div>

          {/* Plain English Data Trust Table */}
          <div className="bg-surface p-6 rounded-2xl border border-border-color shadow-sm space-y-4 premium-card">
            <h2 className="text-lg font-bold text-text-primary flex items-center gap-2">
              <FileCheck className="w-5 h-5 text-primary-600" />
              Data Trust Audit &amp; Business Impact
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-surface-muted text-text-primary font-bold uppercase text-[10px] tracking-wider">
                  <tr>
                    <th className="p-3.5 rounded-l-xl">Dataset Check</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5">Business Impact</th>
                    <th className="p-3.5 rounded-r-xl">Suggested Fix</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-medium text-text-primary">
                  <tr className="hover:bg-surface-muted/50">
                    <td className="p-3.5 font-bold text-text-primary">Order Dates &amp; Timestamps</td>
                    <td className="p-3.5"><span className="px-2 py-0.5 bg-success-100 text-success-800 font-bold rounded">100% Clean</span></td>
                    <td className="p-3.5 text-text-secondary">Enables accurate historical trend forecasting.</td>
                    <td className="p-3.5 text-text-muted">None needed.</td>
                  </tr>
                  <tr className="hover:bg-surface-muted/50">
                    <td className="p-3.5 font-bold text-text-primary">Customer &amp; Payment Links</td>
                    <td className="p-3.5"><span className="px-2 py-0.5 bg-success-100 text-success-800 font-bold rounded">100% Linked</span></td>
                    <td className="p-3.5 text-text-secondary">Ensures accurate customer lifetime value calculation.</td>
                    <td className="p-3.5 text-text-muted">None needed.</td>
                  </tr>
                  <tr className="hover:bg-surface-muted/50">
                    <td className="p-3.5 font-bold text-text-primary">Quantity Field Outlier Spike</td>
                    <td className="p-3.5"><span className="px-2 py-0.5 bg-warning-100 text-warning-800 font-bold rounded">1 Bulk Order Spike</span></td>
                    <td className="p-3.5 text-text-secondary">May slightly skew average order value calculation.</td>
                    <td className="p-3.5 text-primary-600 font-bold">Review bulk order #1094.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
    </div>
  );
}
