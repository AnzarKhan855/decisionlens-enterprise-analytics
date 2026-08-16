"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  HelpCircle,
  BookOpen,
  Sparkles,
  Search,
  FileText,
  Layers,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  Cpu,
} from "lucide-react";

const faqList = [
  {
    q: "What is a Business Workspace?",
    a: "A Business Workspace is a unified container for all your business data. When you upload files, DecisionLens automatically organizes them, detects relationships between tables, and prepares everything for analysis.",
  },
  {
    q: "How does AI analyze my data?",
    a: "DecisionLens scans your data to identify key metrics, trends, and patterns. It classifies columns into categories like revenue, customers, products, and time periods, then calculates KPIs directly from your data.",
  },
  {
    q: "How are charts selected?",
    a: "DecisionLens automatically chooses the best visualization based on your data types. Time-series data gets trend charts, categorical data gets comparison charts, and distributions get breakdown views.",
  },
  {
    q: "How does forecasting work?",
    a: "DecisionLens applies statistical models to your historical data to project future trends. It shows predicted values with confidence intervals so you can plan with realistic expectations.",
  },
  {
    q: "How should I use strategic recommendations?",
    a: "Every recommendation is ranked by business impact. Each includes the expected return, confidence level, timeline, and evidence from your data. Use them to prioritize your initiatives.",
  },
];

const glossaryTerms = [
  { term: "Business Workspace", desc: "A unified container for all your business datasets, automatically organizing tables and relationships." },
  { term: "Analytics Platform", desc: "High-performance analytics platform that processes your data in-memory for fast analysis." },
  { term: "Smart Classification", desc: "AI algorithm that categorizes your data columns into business-relevant groups like revenue, customers, and time periods." },
  { term: "Analysis Score", desc: "A 0-100 score evaluating how well your data supports business analysis." },
  { term: "Business Health Score", desc: "A 0-100 composite score evaluating your business performance across multiple dimensions." },
];

export default function HelpCenterPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(0);

  const filteredGlossary = glossaryTerms.filter(
    (t) =>
      t.term.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.desc.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-5xl mx-auto">
      <div className="bg-background text-text-primary p-8 rounded-2xl shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-6 border border-border-color premium-card">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-widest text-primary-400">
            <HelpCircle className="w-4 h-4" /> Help Center
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight">How DecisionLens Works</h1>
          <p className="text-sm text-text-muted max-w-2xl leading-relaxed">
            Learn how DecisionLens analyzes your data, builds workspaces, and generates business insights.
          </p>
        </div>

        <div className="relative min-w-[280px]">
          <Search className="w-4 h-4 text-text-muted absolute left-3.5 top-3.5" aria-hidden="true" />
          <input
            type="text"
            placeholder="Search help..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-surface-muted border border-border-color rounded-xl text-xs font-semibold text-text-primary focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-text-muted"
          />
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-lg font-extrabold text-text-primary flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-primary-600" />
          Platform Overview
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { icon: <Layers className="w-6 h-6" />, title: "1. Upload Data", desc: "Upload CSV, Excel, or ZIP files. DecisionLens automatically organizes your data into a unified workspace.", color: "indigo" },
            { icon: <Cpu className="w-6 h-6" />, title: "2. AI Analysis", desc: "Our AI analyzes your data to identify key metrics, trends, and business insights automatically.", color: "emerald" },
            { icon: <TrendingUp className="w-6 h-6" />, title: "3. Get Insights", desc: "View executive dashboards, predictions, and actionable recommendations based on your data.", color: "violet" },
          ].map((step, idx) => (
              <div key={idx} className={`bg-surface p-6 rounded-2xl border border-border-color shadow-sm space-y-3 premium-card`}>
                <div className={`p-3 bg-${step.color}-50 text-${step.color}-600 rounded-2xl w-fit`}>
                  {step.icon}
                </div>
                <h3 className="text-base font-extrabold text-text-primary">{step.title}</h3>
              <p className="text-xs text-text-muted leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-surface p-7 rounded-2xl border border-border-color shadow-sm space-y-4 premium-card">
        <h2 className="text-lg font-extrabold text-text-primary flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-primary-600" />
          Frequently Asked Questions
        </h2>

        <div className="space-y-3">
          {faqList.map((faq, idx) => {
            const isOpen = openFaqIndex === idx;
            return (
              <div key={idx} className="border border-border-color rounded-2xl overflow-hidden">
                <button
                  onClick={() => setOpenFaqIndex(isOpen ? null : idx)}
                  className="w-full p-4 bg-surface-muted hover:bg-surface-muted/80 transition-colors flex items-center justify-between text-left"
                  aria-expanded={isOpen}
                >
                  <span className="text-xs font-bold text-text-primary">{faq.q}</span>
                  {isOpen ? <ChevronUp className="w-4 h-4 text-text-muted" aria-hidden="true" /> : <ChevronDown className="w-4 h-4 text-text-muted" aria-hidden="true" />}
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="p-4 bg-surface text-xs text-text-secondary leading-relaxed border-t border-border-light font-medium">
                        {faq.a}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </div>

      <div className="bg-surface p-7 rounded-2xl border border-border-color shadow-sm space-y-4 premium-card">
        <h2 className="text-lg font-extrabold text-text-primary flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary-600" />
          Business Glossary
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-muted text-text-primary font-bold uppercase text-[10px] tracking-wider">
              <tr>
                <th className="p-3.5 rounded-l-xl">Term</th>
                <th className="p-3.5 rounded-r-xl">Definition</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-text-primary">
              {filteredGlossary.map((g, idx) => (
                <tr key={idx} className="hover:bg-surface-muted/50">
                  <td className="p-3.5 font-extrabold text-primary-600">{g.term}</td>
                  <td className="p-3.5 text-text-secondary leading-relaxed font-medium">{g.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
