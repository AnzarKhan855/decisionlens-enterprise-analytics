"use client";

import React, { useState } from "react";
import { usePathname } from "next/navigation";
import { HelpCircle, X, CheckCircle2, BookOpen, Lightbulb, Target, ArrowRight } from "lucide-react";

interface ContextualHelp {
  title: string;
  subtitle: string;
  what_is_this: string;
  why_useful: string;
  questions_answered: string[];
  how_to_use: string;
}

const PAGE_HELP_MAP: Record<string, ContextualHelp> = {
  "/": {
    title: "Executive Business Workspace Library",
    subtitle: "Central portfolio of all enterprise business workspaces",
    what_is_this: "This page stores all of your uploaded business datasets. Every uploaded ZIP archive becomes a unified Business Workspace where all connected datasets are automatically joined into an OLAP analytical model.",
    why_useful: "Allows non-technical business owners and executives to manage multi-table datasets as high-level business portfolios without needing database administration skills.",
    questions_answered: [
      "What business workspaces are currently active in my enterprise?",
      "What is the overall business health and data quality score of my uploaded workspace?",
      "Are my business datasets ready for AI strategy consulting and ML forecasting?",
      "How many total orders, products, and customers exist in this business model?"
    ],
    how_to_use: "Click 'Open Workspace' to view executive dashboard KPIs, or click 'Dataset Explorer' to inspect friendly table layouts and relationships."
  },
  "/datasets": {
    title: "Executive Business Workspace Catalog",
    subtitle: "Portfolio management of all enterprise business workspaces",
    what_is_this: "This page stores all of your uploaded businesses. Every ZIP archive becomes one Business Workspace where all related datasets are automatically connected into a unified semantic model.",
    why_useful: "Eliminates file management complexity by organizing data into clean business entities instead of scattered CSV files.",
    questions_answered: [
      "Which business workspaces are loaded and ready for analysis?",
      "What is the health score and row count of each uploaded workspace?",
      "How do I permanently delete an old business workspace?"
    ],
    how_to_use: "Select 'Open Workspace' to launch analytics, or click 'Business Profile' to read executive business background information."
  },
  "/explorer": {
    title: "Executive Dataset Explorer",
    subtitle: "Inspect business table structures and relationships in plain English",
    what_is_this: "The Dataset Explorer presents all tables in your Business Workspace with friendly human names (Orders, Customers, Products, Payments) instead of raw filenames.",
    why_useful: "Allows executives and auditors to verify primary keys, foreign keys, row counts, and data quality without writing complex queries.",
    questions_answered: [
      "What primary tables make up my Business Workspace?",
      "What is the data quality score for each specific table?",
      "How are Orders connected to Customers, Products, and Payments?"
    ],
    how_to_use: "Click any table tab to view column dictionaries, primary keys, foreign key connections, and row samples."
  },
  "/profile": {
    title: "Executive Business Profile",
    subtitle: "AI-generated business background summary and capability matrix",
    what_is_this: "The Business Profile is an automatically synthesized executive summary of your uploaded business model, industry, revenue structure, and analytical capabilities.",
    why_useful: "Serves as an instant briefing document for executive stakeholders before diving into analytical dashboards.",
    questions_answered: [
      "What industry and business model does this dataset represent?",
      "What products, customers, and sales channels are included?",
      "Which strategic business questions can be answered by this workspace?"
    ],
    how_to_use: "Review main KPIs, ready capabilities, and executive questions before opening the interactive dashboard."
  },
  "/dynamic-dashboard": {
    title: "Executive Decision Intelligence Dashboard",
    subtitle: "Real-time KPIs, automated visualizations, and McKinsey AI consulting",
    what_is_this: "The central executive dashboard providing top-line revenue, order volumes, automated charts, ML forecasts, and RAG AI consulting.",
    why_useful: "Synthesizes empirical dataset facts into clear business answers in under 5 minutes without manual configuration.",
    questions_answered: [
      "What is my total revenue, average order value, and gross order volume?",
      "Which product categories generate the highest total sales?",
      "What is the AI-recommended strategy to increase profit margins?"
    ],
    how_to_use: "Review top-line KPIs, explore automatically generated charts, and ask the AI Business Consultant custom strategy questions."
  },
  "/data-quality": {
    title: "Can I Trust My Data?",
    subtitle: "Data trust score, completeness evaluation, and anomaly audit",
    what_is_this: "This page evaluates whether your uploaded dataset is complete, accurate, and free of broken relationships before making financial decisions.",
    why_useful: "Prevents making costly business decisions on corrupted, duplicate, or incomplete dataset records.",
    questions_answered: [
      "Can leadership trust the calculated KPIs and financial metrics?",
      "Are there missing values, broken dates, or duplicate records?",
      "What is the overall confidence score of my data model?"
    ],
    how_to_use: "Check the overall Trust Score badge and review recommended automated data quality fixes."
  },
  "/lineage": {
    title: "How Your Data Flows",
    subtitle: "End-to-end data pipeline & transformation visualizer",
    what_is_this: "A step-by-step visual map showing how raw ZIP files are converted into analytics tables, semantic models, KPIs, forecasts, and AI recommendations.",
    why_useful: "Provides 100% data auditability and transparency so executives know exactly how metrics were calculated.",
    questions_answered: [
      "How does DecisionLens process uploaded ZIP archives?",
      "At what stage are foreign keys and relationships discovered?",
      "How do raw transaction rows become executive recommendations?"
    ],
    how_to_use: "Click any process step to view input data, processing systems, and resulting output artifacts."
  },
  "/architecture": {
    title: "Interactive System Architecture",
    subtitle: "3D component explorer of the DecisionLens intelligence engine",
    what_is_this: "An interactive architectural breakdown of DecisionLens systems (AI System, Forecast System, Analytics Platform, RAG Engine, Parquet Storage).",
    why_useful: "Demonstrates enterprise-grade security, zero-copy columnar storage, and Microsoft Fabric-class OLAP performance.",
    questions_answered: [
      "Which technologies power the DecisionLens analytics platform?",
      "How are AI queries executed safely without data leakage?",
      "What technologies handle high-speed in-memory queries?"
    ],
    how_to_use: "Click any component node to inspect inputs, outputs, technologies, and business values."
  }
};

export default function GlobalHelpDrawer() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  const helpContent: ContextualHelp = PAGE_HELP_MAP[pathname] || {
    title: "DecisionLens Executive Platform",
    subtitle: "Enterprise Decision Intelligence OS",
    what_is_this: "DecisionLens is an Enterprise Decision Intelligence Platform that converts multi-table ZIP business datasets into unified semantic models, KPIs, forecasts, and AI business consulting.",
    why_useful: "Designed for non-technical CEOs, Founders, CFOs, and Operations Managers to understand their business performance instantly.",
    questions_answered: [
      "How do I upload business files?",
      "How are KPIs calculated empirically?",
      "How does the AI Business Consultant operate?"
    ],
    how_to_use: "Use the sidebar navigation to switch between Workspaces, Dashboard, Data Flow, and Data Quality."
  };

  return (
    <>
      {/* Floating Header Help CTA */}
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-50 hover:bg-primary-100 text-primary-700 text-xs font-bold rounded-xl transition-all border border-primary-200 shadow-sm"
        title="Open Page Help & Executive Guide"
      >
        <HelpCircle className="w-4 h-4 text-primary-600" />
        <span>Help Guide</span>
      </button>

      {/* Slide-over Help Drawer */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-background/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg h-full flex flex-col justify-between overflow-y-auto premium-card">
            {/* Header */}
            <div className="p-6 bg-gradient-to-r from-surface via-primary-50 to-surface dark:from-background dark:via-primary-800 dark:to-background text-text-primary flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-primary-400">Executive Guide</span>
                <h3 className="text-xl font-extrabold mt-0.5">{helpContent.title}</h3>
                <p className="text-xs text-text-muted mt-0.5">{helpContent.subtitle}</p>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-2 bg-surface/10 hover:bg-surface/20 text-text-primary rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body Content */}
            <div className="p-6 space-y-6 flex-1 text-xs leading-relaxed text-text-primary">
              {/* Question 1: What is this page? */}
              <div className="p-4 bg-primary-50/70 border border-primary-100 rounded-2xl space-y-2">
                <div className="flex items-center gap-2 text-primary-800 font-bold text-sm">
                  <BookOpen className="w-4 h-4 text-primary-600" />
                  <span>What is this page?</span>
                </div>
                <p className="text-text-primary">{helpContent.what_is_this}</p>
              </div>

              {/* Question 2: Why is it useful? */}
              <div className="p-4 bg-success-50/70 border border-success-100 rounded-2xl space-y-2">
                <div className="flex items-center gap-2 text-success-800 font-bold text-sm">
                  <Lightbulb className="w-4 h-4 text-success-600" />
                  <span>Why is it useful for business leaders?</span>
                </div>
                <p className="text-text-primary">{helpContent.why_useful}</p>
              </div>

              {/* Question 3: What business questions does it answer? */}
              <div className="p-4 bg-surface-muted border border-border-color rounded-2xl space-y-2">
                <div className="flex items-center gap-2 text-text-primary font-bold text-sm">
                  <Target className="w-4 h-4 text-primary-600" />
                  <span>What business questions does it answer?</span>
                </div>
                <ul className="space-y-2 mt-2">
                  {helpContent.questions_answered.map((q, idx) => (
                     <li key={idx} className="flex items-start gap-2 text-text-primary font-medium">
                      <CheckCircle2 className="w-4 h-4 text-success-500 mt-0.5 flex-shrink-0" />
                      <span>{q}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Question 4: How to use */}
              <div className="p-4 bg-primary-50/70 border border-primary-100 rounded-2xl space-y-2">
                <div className="flex items-center gap-2 text-primary-800 font-bold text-sm">
                  <ArrowRight className="w-4 h-4 text-primary-600" />
                  <span>How should executives use it?</span>
                </div>
                <p className="text-text-primary">{helpContent.how_to_use}</p>
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 bg-surface-muted border-t border-border-color text-center">
              <button
                onClick={() => setIsOpen(false)}
                className="w-full py-2.5 bg-primary-600 hover:bg-primary-700 text-white font-bold text-xs rounded-xl transition-all shadow-md"
              >
                Close Executive Help Guide
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
