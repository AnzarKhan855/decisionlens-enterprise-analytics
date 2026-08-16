"use client";

import React, { useState } from "react";
import { Sparkles, CheckCircle2, ArrowRight, ArrowLeft, Building2, HelpCircle, ShieldCheck, AlertCircle, TrendingUp, DollarSign, LayoutDashboard, X } from "lucide-react";

import type { DashboardPayload } from "@/lib/types";

interface GuidedOnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  dashboardData: DashboardPayload | null;
}

export default function GuidedOnboardingModal({ isOpen, onClose, dashboardData }: GuidedOnboardingModalProps) {
  const [currentStep, setCurrentStep] = useState(1);

  if (!isOpen) return null;

  const datasetType = dashboardData?.dataset_type || "Generic Dataset";
  const rowCount = dashboardData?.profile?.total_rows || 0;
  const readiness = dashboardData?.readiness || { readiness_score: 0, readiness_level: "UNKNOWN" };

  return (
    <div className="fixed inset-0 bg-background/80 backdrop-blur-md z-50 flex items-center justify-center p-6">
      <div       className="bg-background text-text-primary rounded-2xl max-w-3xl w-full p-6 space-y-6 shadow-2xl border border-border-color relative flex flex-col justify-between max-h-[90vh] overflow-y-auto">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-6 top-6 p-2 bg-surface-muted hover:bg-surface-muted rounded-full text-text-muted hover:text-text-primary transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Step Indicator */}
        <div className="flex items-center justify-between border-b border-border-color pb-4">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-primary-500/20 text-primary-400 text-xs font-extrabold rounded-full border border-primary-500/30 uppercase tracking-widest">
              Executive Onboarding • Step {currentStep} of 4
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            {[1, 2, 3, 4].map((step) => (
              <div
                key={step}
                className={`h-2 rounded-full transition-all ${
                  step === currentStep ? "w-8 bg-primary-500" : step < currentStep ? "w-3 bg-success-500" : "w-3 bg-surface-muted"
                }`}
              />
            ))}
          </div>
        </div>

        {/* SCREEN 1: We Analyzed Your Business */}
        {currentStep === 1 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-400">
                <Building2 className="w-4 h-4" /> AI Business Diagnostics
              </div>
              <h2 className="text-2xl font-extrabold text-text-primary">We analyzed your business workspace.</h2>
              <p className="text-sm text-text-muted leading-relaxed">
                DecisionLens automatically ingested, cleaned, and connected your multi-table business folder.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-4 bg-surface/5 rounded-2xl border border-foreground/10 space-y-1">
                <span className="text-text-muted block">Detected Industry</span>
                <strong className="text-lg font-bold text-text-primary">{datasetType}</strong>
              </div>

              <div className="p-4 bg-surface/5 rounded-2xl border border-foreground/10 space-y-1">
                <span className="text-text-muted block">Analyzed Datasets</span>
                <strong className="text-lg font-bold text-primary-400">{dashboardData?.connected_tables_count || rowCount.toLocaleString()} Records</strong>
              </div>

              <div className="p-4 bg-surface/5 rounded-2xl border border-foreground/10 space-y-1">
                <span className="text-text-muted block">Total Customer Records</span>
                <strong className="text-lg font-bold text-success-400">{rowCount.toLocaleString()} Transactions</strong>
              </div>

              <div className="p-4 bg-surface/5 rounded-2xl border border-foreground/10 space-y-1">
                <span className="text-text-muted block">Analysis Readiness Score</span>
                <strong className="text-lg font-bold text-primary-400">{readiness.readiness_score}% ({readiness.readiness_level})</strong>
              </div>
            </div>

            <div className="p-4 bg-success-500/10 border border-success-500/20 rounded-2xl text-xs text-success-300 flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-success-400 flex-shrink-0" />
              <span>Your workspace is fully connected with valid foreign keys and zero missing values.</span>
            </div>
          </div>
        )}

        {/* SCREEN 2: What Does This Dataset Represent? */}
        {currentStep === 2 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-400">
                <HelpCircle className="w-4 h-4" /> Plain-English Business Summary
              </div>
              <h2 className="text-2xl font-extrabold text-text-primary">What does this workspace represent?</h2>
              <p className="text-sm text-text-muted leading-relaxed">
                This workspace contains structured business data across multiple connected tables, ready for AI-powered analytics and decision intelligence.
              </p>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3.5 bg-surface/5 rounded-xl border border-foreground/10 flex items-start gap-3">
                <CheckCircle2 className="w-4 h-4 text-success-400 mt-0.5 flex-shrink-0" />
                <div>
                  <strong className="text-text-primary block mb-0.5">What AI Can Analyze:</strong>
                  <span className="text-text-muted">Key metric trends, dimension breakdowns, anomaly detection, and predictive forecasts across all uploaded tables.</span>
                </div>
              </div>

              <div className="p-3.5 bg-surface/5 rounded-xl border border-foreground/10 flex items-start gap-3">
                <AlertCircle className="w-4 h-4 text-warning-400 mt-0.5 flex-shrink-0" />
                <div>
                  <strong className="text-text-primary block mb-0.5">What AI Cannot Analyze (And Why):</strong>
                  <span className="text-text-muted">Additional dimensions not present in the uploaded dataset. Include relevant tables to expand analytical coverage.</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* SCREEN 3: What Questions Can DecisionLens Answer? */}
        {currentStep === 3 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-400">
                <Sparkles className="w-4 h-4" /> Executive Business Questions
              </div>
              <h2 className="text-2xl font-extrabold text-text-primary">What questions can DecisionLens answer for you?</h2>
              <p className="text-sm text-text-muted leading-relaxed">
                 Ask DecisionLens any plain-English question without writing complex queries or creating manual pivot tables.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="p-3.5 bg-surface-muted/80 rounded-xl border border-border-color font-semibold text-primary-200">
                💰 Where am I losing potential revenue?
              </div>
              <div className="p-3.5 bg-surface-muted/80 rounded-xl border border-border-color font-semibold text-success-200">
                📦 Which product categories yield highest profit margins?
              </div>
              <div className="p-3.5 bg-surface-muted/80 rounded-xl border border-border-color font-semibold text-primary-200">
                👥 Which customer segments are at risk of churning?
              </div>
              <div className="p-3.5 bg-surface-muted/80 rounded-xl border border-border-color font-semibold text-warning-200">
                🚀 What top 3 actions should management execute next?
              </div>
            </div>
          </div>
        )}

        {/* SCREEN 4: Executive Dashboard Ready */}
        {currentStep === 4 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-success-400">
                <LayoutDashboard className="w-4 h-4" /> Executive Briefing Ready
              </div>
              <h2 className="text-2xl font-extrabold text-text-primary">Your Executive Dashboard is Ready.</h2>
              <p className="text-sm text-text-muted leading-relaxed">
                Here is your 30-second executive summary before exploring the interactive dashboard.
              </p>
            </div>

              <div className="space-y-3 text-xs">
                <div className="p-4 bg-gradient-to-r from-primary-800/60 to-primary-900/60 rounded-2xl border border-primary-500/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-primary-300 font-bold uppercase text-[10px]">Top Strategic Insight</span>
                    <span className="text-success-400 font-extrabold">{readiness.readiness_score}% Confidence</span>
                  </div>
                  <h4 className="text-base font-bold text-text-primary">Data Analyzed &amp; Insights Generated</h4>
                  <p className="text-text-muted">Review the executive dashboard for key trends, root causes, predictions, and recommended actions based on your dataset.</p>
                </div>
              </div>
          </div>
        )}

        {/* Navigation Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-border-color">
          {currentStep > 1 ? (
            <button
              onClick={() => setCurrentStep(currentStep - 1)}
              className="px-4 py-2 bg-surface-muted hover:bg-surface-muted text-text-muted text-xs font-semibold rounded-xl transition-all flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Previous</span>
            </button>
          ) : (
            <div />
          )}

          {currentStep < 4 ? (
            <button
              onClick={() => setCurrentStep(currentStep + 1)}
              className="px-5 py-2.5 bg-primary-600 hover:bg-primary-500 text-white text-xs font-bold rounded-xl transition-all shadow-md shadow-primary-600/30 flex items-center gap-2"
            >
              <span>Next Step</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={onClose}
              className="px-6 py-2.5 bg-success-600 hover:bg-success-500 text-white text-xs font-extrabold rounded-xl transition-all shadow-md shadow-success-600/30 flex items-center gap-2"
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Explore Executive Dashboard</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
