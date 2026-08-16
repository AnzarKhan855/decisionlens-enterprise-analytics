"use client";

import React, { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import {
  GitCommit,
  UploadCloud,
  FileText,
  Layers,
  BarChart2,
  TrendingUp,
  Sparkles,
  CheckCircle2,
  ArrowRight,
  Info
} from "lucide-react";

const flowStages = [
  {
    stage: "1. Upload Folder",
    icon: UploadCloud,
    color: "bg-primary-50 border-primary-200 text-primary-700",
    title: "Raw Business Upload",
    description: "You upload a ZIP archive or folder containing CSV files (e.g. orders, customers, products)."
  },
  {
    stage: "2. AI Reads Files",
    icon: FileText,
    color: "bg-sky-50 border-sky-200 text-sky-700",
    title: "Schema Inspection",
    description: "AI profiles columns, distinguishes measures (sales, price) from dimensions (category, region)."
  },
  {
    stage: "3. Relationships Detected",
    icon: Layers,
    color: "bg-teal-50 border-teal-200 text-teal-700",
    title: "1:N Join Graph",
    description: "Detects customer_id, order_id, product_id foreign keys to link tables automatically."
  },
  {
    stage: "4. Business Model",
    icon: BarChart2,
    color: "bg-warning-50 border-warning-200 text-warning-700",
    title: "Semantic Business Layer",
    description: "Builds a unified analytical view combining transactions, customers, and product catalogs."
  },
  {
    stage: "5. KPIs & Forecast",
    icon: TrendingUp,
    color: "bg-primary-50 border-primary-200 text-primary-700",
    title: "Predictive Analytics",
    description: "Calculates total revenue, profit margin, growth trends, and 14-day predictive forecasts."
  },
  {
    stage: "6. Strategic Recommendations",
    icon: Sparkles,
    color: "bg-success-50 border-success-200 text-success-700",
    title: "McKinsey Prescriptive AI",
    description: "Generates top 3 evidence-backed strategic actions with projected financial impact ($)."
  }
];

export default function HowDataFlowsPage() {
  const [activeStage, setActiveStage] = useState(0);

  return (
    <div className="p-8 space-y-8">
          {/* Header Banner */}
          <div className="bg-background text-text-primary p-8 rounded-2xl shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-6 border border-border-color premium-card">
            <div>
              <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-widest text-primary-400 mb-1">
                <GitCommit className="w-4 h-4" /> Visual Data Journey
              </div>
              <h1 className="text-3xl font-extrabold tracking-tight">How Your Data Flows</h1>
              <p className="text-sm text-text-muted max-w-2xl mt-1 leading-relaxed">
                See how DecisionLens transforms your raw CSV files into linked business workspaces, predictive forecasts, and executive recommendations.
              </p>
            </div>

            <div className="px-4 py-2.5 bg-success-500/20 text-success-300 text-xs font-bold rounded-xl border border-success-500/30 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-success-400" />
              <span>Automatic 6-Stage Process</span>
            </div>
          </div>

          {/* Interactive Step-by-Step Flow Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {flowStages.map((st, idx) => {
              const Icon = st.icon;
              const isActive = activeStage === idx;
              return (
                <div
                  key={idx}
                  onClick={() => setActiveStage(idx)}
                  className={`p-4 rounded-2xl border cursor-pointer transition-all flex flex-col justify-between space-y-3 ${
                    isActive
                      ? "bg-primary-600 text-white border-primary-600 shadow-lg scale-105"
                      : "bg-surface text-text-primary border-border-color hover:border-primary-300 hover:shadow-md"
                  }`}
                >
                  <div className="space-y-2">
                    <div className={`p-2.5 rounded-xl w-fit ${isActive ? "bg-surface/20 text-primary-600 dark:text-white" : st.color}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className={`text-[10px] font-mono uppercase tracking-wider block font-bold ${isActive ? "text-primary-200" : "text-text-muted"}`}>
                      Stage {idx + 1}
                    </span>
                    <h3 className="text-sm font-bold line-clamp-1">{st.title}</h3>
                  </div>

                  <div className={`text-[11px] leading-relaxed line-clamp-3 ${isActive ? "text-primary-100" : "text-text-muted"}`}>
                    {st.description}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Detailed Active Stage Explanation Card */}
          <div className="bg-surface p-6 rounded-2xl border border-border-color shadow-sm space-y-4 premium-card">
            <div className="flex items-center gap-3 border-b border-border-light pb-3">
              <div className="p-3 bg-primary-50 text-primary-600 rounded-xl">
                <Info className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-semibold uppercase text-primary-600">Stage Breakdown</span>
                <h3 className="text-lg font-bold text-text-primary">{flowStages[activeStage].title}</h3>
              </div>
            </div>

            <p className="text-sm text-text-secondary leading-relaxed max-w-3xl">
              {flowStages[activeStage].description} DecisionLens handles all data cleaning, foreign key linking, and statistical forecasting behind the scenes so business leaders never need to write SQL queries.
            </p>
          </div>
    </div>
  );
}
