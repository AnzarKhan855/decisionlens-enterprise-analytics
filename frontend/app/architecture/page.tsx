"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import {
  Layers,
  Database,
  Cpu,
  Bot,
  CheckCircle2,
  ArrowRight,
  Server,
  LayoutDashboard,
  Zap,
  Activity,
  HardDrive,
  Lock,
  GitBranch,
  TrendingUp,
  FileText,
  Code2,
  Info,
  Sliders,
  Target,
  FileSpreadsheet,
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from "lucide-react";

interface ArchStage {
  id: string;
  name: string;
  stageNum: number;
  category: "client" | "gateway" | "security" | "ingestion" | "analytics" | "ai" | "outputs" | "storage";
  icon: any;
  color: string;
  bgGlow: string;
  description: string;
  tech: string[];
  sourcePath: string;
  keyFunctions: string[];
}

const PIPELINE_STAGES: ArchStage[] = [
  {
    id: "user",
    name: "1. USER INTERFACE",
    stageNum: 1,
    category: "client",
    icon: LayoutDashboard,
    color: "from-info-500 to-info-600",
    bgGlow: "rgba(59, 130, 246, 0.15)",
    description: "Role-aware executive dashboard presenting real-time KPIs, Recharts visualizations, scenario levers, and Copilot chat.",
    tech: ["React 19", "Next.js 16 App Router", "TailwindCSS", "Recharts"],
    sourcePath: "frontend/app/dynamic-dashboard/page.tsx",
    keyFunctions: ["Role-Based Access Rendering", "Dynamic Workspace State Sync", "Interactive Scenario Controls"],
  },
  {
    id: "frontend",
    name: "2. FRONTEND APPLICATION",
    stageNum: 2,
    category: "client",
    icon: Code2,
    color: "from-primary-500 to-primary-600",
    bgGlow: "rgba(79, 70, 229, 0.15)",
    description: "TypeScript web client managing state, Axios request interceptors, Bearer token injection, and toast notifications.",
    tech: ["TypeScript", "Axios Interceptors", "Framer Motion"],
    sourcePath: "frontend/lib/api.ts",
    keyFunctions: ["JWT Bearer Token Injection", "Workspace State Persistence", "API Error Normalization"],
  },
  {
    id: "api_gateway",
    name: "3. API GATEWAY",
    stageNum: 3,
    category: "gateway",
    icon: Server,
    color: "from-primary-500 to-primary-600",
    bgGlow: "rgba(139, 92, 246, 0.15)",
    description: "High-performance Python API gateway running on Uvicorn ASGI server with Pydantic v2 payload validation.",
    tech: ["FastAPI", "Uvicorn ASGI", "Pydantic v2"],
    sourcePath: "backend/app/main.py",
    keyFunctions: ["CORS Middleware Management", "Structured JSON Request Logging", "Route Dispatching"],
  },
  {
    id: "authentication",
    name: "4. AUTHENTICATION & RBAC",
    stageNum: 4,
    category: "security",
    icon: Lock,
    color: "from-success-500 to-success-600",
    bgGlow: "rgba(16, 185, 129, 0.15)",
    description: "Multi-tenant access control enforcing Super Admin, Executive, and Analyst permissions with JWT tokens.",
    tech: ["PyJWT", "Passlib (Bcrypt)", "OAuth2 Scheme"],
    sourcePath: "backend/app/core/rbac.py",
    keyFunctions: ["JWT Token Generation & Verification", "Role-Based Endpoint Protection", "Super-Admin OTP Verification"],
  },
  {
    id: "data_ingestion",
    name: "5. DATA INGESTION",
    stageNum: 5,
    category: "ingestion",
    icon: FileSpreadsheet,
    color: "from-warning-500 to-warning-600",
    bgGlow: "rgba(245, 158, 11, 0.15)",
    description: "Ingests CSV, Excel, and Parquet files. Converts raw tables into DuckDB columnar format with SHA256 deduplication.",
    tech: ["DuckDB read_csv_auto", "PyArrow", "Pandas"],
    sourcePath: "backend/app/ingestion/generic_loader.py",
    keyFunctions: ["Automatic Delimiter Detection", "Parquet Columnar Storage Conversion", "File Deduplication"],
  },
  {
    id: "data_profiling",
    name: "6. DATA PROFILING",
    stageNum: 6,
    category: "ingestion",
    icon: Zap,
    color: "from-error-500 to-error-600",
    bgGlow: "rgba(244, 63, 94, 0.15)",
    description: "Profiles uploaded datasets to compute column data types, value distributions, missing data rates, and numeric aggregates.",
    tech: ["DuckDB SUM/AVG Profiling", "NumPy", "Pandas Profiler"],
    sourcePath: "backend/app/ingestion/semantic_profiler.py",
    keyFunctions: ["Numeric SUM/AVG Aggregation", "Column Classification (Measures/Dimensions)", "Data Completeness Scoring"],
  },
  {
    id: "semantic_model",
    name: "7. SEMANTIC MODEL ENGINE",
    stageNum: 7,
    category: "analytics",
    icon: GitBranch,
    color: "from-info-500 to-info-600",
    bgGlow: "rgba(14, 165, 233, 0.15)",
    description: "Automatically detects business domains (Retail, Finance, Health, HR) and entity/metric/relationship mappings.",
    tech: ["Python", "NetworkX", "Graph Matching"],
    sourcePath: "backend/app/semantic_model/engine.py",
    keyFunctions: ["Domain Classification", "Business Entity Detection", "Metric & Relationship Mapping"],
  },
  {
    id: "analytics_engine",
    name: "8. UNIVERSAL ANALYTICS ENGINE",
    stageNum: 8,
    category: "analytics",
    icon: Cpu,
    color: "from-primary-500 to-primary-600",
    bgGlow: "rgba(99, 102, 241, 0.15)",
    description: "The core statistical engine orchestrating KPI calculation, growth/decline rates, rankings, distributions, and variance decomposition.",
    tech: ["UniversalAnalyticsEngine", "DuckDB Vectorized OLAP", "SciPy"],
    sourcePath: "backend/app/analytics/universal_engine.py",
    keyFunctions: ["Canonical Dataset Profile Generation", "Variance Decomposition & Root Cause", "Statistical Outlier Detection"],
  },
  {
    id: "forecasting_engine",
    name: "9. FORECASTING ENGINE",
    stageNum: 9,
    category: "analytics",
    icon: TrendingUp,
    color: "from-success-500 to-success-600",
    bgGlow: "rgba(16, 185, 129, 0.15)",
    description: "Dual-mode forecasting engine: Mode A (Temporal Time-Series Projections) and Mode B (Data-Driven Baseline Analysis).",
    tech: ["UniversalPredictionEngine", "OLS Regression", "Statsmodels"],
    sourcePath: "backend/app/ml/prediction_engine.py",
    keyFunctions: ["Mode A Time-Series Projections", "Mode B Baseline Predictive Analysis", "95% Prediction Interval Calculation"],
  },
  {
    id: "scenario_engine",
    name: "10. SCENARIO SIMULATION ENGINE",
    stageNum: 10,
    category: "analytics",
    icon: Sliders,
    color: "from-warning-500 to-warning-600",
    bgGlow: "rgba(245, 158, 11, 0.15)",
    description: "Discovers numeric levers and computes before/after KPI impact simulations based on user lever adjustments.",
    tech: ["ScenarioLeverEngine", "Dynamic Sensitivity Matrix"],
    sourcePath: "backend/app/services/scenario_lever_engine.py",
    keyFunctions: ["Continuous Numeric Lever Discovery", "Sensitivity Matrix Projection", "Before/After KPI Impact Calculation"],
  },
  {
    id: "ai_copilot",
    name: "11. UNIVERSAL AI COPILOT",
    stageNum: 11,
    category: "ai",
    icon: Bot,
    color: "from-primary-500 to-primary-600",
    bgGlow: "rgba(217, 70, 239, 0.15)",
    description: "Single cognitive reasoning pipeline parsing intent, executing DuckDB SQL queries, and assembling evidence-backed answers.",
    tech: ["UniversalAIBrain", "Groq LLM API", "Answer Validation Layer"],
    sourcePath: "backend/app/ai/universal_copilot_brain.py",
    keyFunctions: ["Intent Classification (Trends, Anomalies, Recs)", "Anti-Hallucination SQL Grounding", "Question-Specific Answer Assembly"],
  },
  {
    id: "strategy_engine",
    name: "12. STRATEGY ENGINE",
    stageNum: 12,
    category: "outputs",
    icon: Target,
    color: "from-error-500 to-error-600",
    bgGlow: "rgba(244, 63, 94, 0.15)",
    description: "Derives Strategic Priorities #1, #2, #3, Growth Opportunities, and Risk Matrices directly from canonical evidence.",
    tech: ["RecommendationEngine", "BusinessHealthEngine"],
    sourcePath: "backend/app/analytics/recommendation_engine.py",
    keyFunctions: ["Strategic Priority Formulation", "Evidence-Backed Risk Matrix", "Operational Action Item Assignment"],
  },
  {
    id: "reporting",
    name: "13. BOARD REPORTING ENGINE",
    stageNum: 13,
    category: "outputs",
    icon: FileText,
    color: "from-primary-500 to-primary-600",
    bgGlow: "rgba(99, 102, 241, 0.15)",
    description: "Generates 13-section Executive Board Reports and PDF/DOCX exports directly from canonical workspace context.",
    tech: ["UniversalExecutiveReportEngine", "ReportLab", "python-docx"],
    sourcePath: "backend/app/reports/executive_report_engine.py",
    keyFunctions: ["Executive Summary Generation", "30-90-180 Day Action Plan", "PDF / DOCX Export Generation"],
  },
  {
    id: "storage",
    name: "14. DATABASE & STORAGE WAREHOUSE",
    stageNum: 14,
    category: "storage",
    icon: HardDrive,
    color: "from-text-muted to-surface-muted",
    bgGlow: "rgba(71, 85, 105, 0.15)",
    description: "Vectorized DuckDB in-memory OLAP query engine backed by Apache Parquet files, SQLite relational DB, and MongoDB Atlas.",
    tech: ["DuckDB Engine", "Apache Parquet", "SQLite SQLAlchemy", "MongoDB Atlas"],
    sourcePath: "backend/app/database/duckdb_engine.py",
    keyFunctions: ["Vectorized SQL Query Execution", "Columnar Parquet File Storage", "Audit Log & Business Memory Storage"],
  },
];

export default function ArchitecturePage() {
  const [selectedStage, setSelectedStage] = useState<ArchStage | null>(PIPELINE_STAGES[7]);
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [zoomLevel, setZoomLevel] = useState<number>(100);

  const filteredStages = PIPELINE_STAGES.filter(
    (s) => filterCategory === "all" || s.category === filterCategory
  );

  return (
    <main className="p-6 lg:p-10 space-y-8 max-w-7xl mx-auto w-full font-sans">
          {/* Header Banner */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border-color/80">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary-400 mb-1">
                <Layers className="w-4 h-4" />
                <span>Enterprise Architecture</span>
              </div>
              <h1 className="text-3xl font-extrabold text-text-primary tracking-tight">
                14-Stage System Pipeline Map
              </h1>
              <p className="text-sm text-text-muted mt-1">
                End-to-end data flow: User Client → API Gateway → Ingestion → Universal Analytics → Forecasting → AI Copilot → Reports → Storage.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="bg-background border border-border-color rounded-xl p-1 flex items-center gap-1">
                <button
                  onClick={() => setZoomLevel((z) => Math.max(80, z - 10))}
                  className="p-1.5 hover:bg-surface-muted rounded-lg text-text-muted hover:text-text-primary transition"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <span className="text-xs font-mono px-2 text-text-muted font-bold">{zoomLevel}%</span>
                <button
                  onClick={() => setZoomLevel((z) => Math.min(120, z + 10))}
                  className="p-1.5 hover:bg-surface-muted rounded-lg text-text-muted hover:text-text-primary transition"
                  title="Zoom In"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setZoomLevel(100)}
                  className="p-1.5 hover:bg-surface-muted rounded-lg text-text-muted hover:text-text-primary transition ml-1"
                  title="Reset Zoom"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              </div>

              <span className="px-3 py-1.5 bg-success-500/10 text-success-400 border border-success-500/20 text-xs font-semibold rounded-full flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                14 Pipeline Stages Verified
              </span>
            </div>
          </div>

          {/* Category Filter Pills */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-text-muted mr-2">Filter Layer:</span>
            {[
              { id: "all", label: "All 14 Stages" },
              { id: "client", label: "Client & UI" },
              { id: "gateway", label: "Gateway & Auth" },
              { id: "ingestion", label: "Ingestion & Profiling" },
              { id: "analytics", label: "Analytics & ML" },
              { id: "ai", label: "AI Copilot" },
              { id: "outputs", label: "Strategy & Reports" },
              { id: "storage", label: "Data Storage" },
            ].map((cat) => (
              <button
                key={cat.id}
                onClick={() => setFilterCategory(cat.id)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-xl border transition-all ${
                  filterCategory === cat.id
                    ? "bg-primary-600 text-white border-primary-500 shadow-md shadow-primary-600/30"
                    : "bg-background/80 text-text-muted border-border-color hover:border-border-color hover:text-text-primary"
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* Pipeline Map & Inspector Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8" style={{ zoom: `${zoomLevel}%` }}>
            {/* Stage List (7 Cols) */}
            <div className="lg:col-span-7 space-y-3">
              <h2 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Activity className="w-4 h-4 text-primary-400" />
                <span>Sequential Data Flow Pipeline</span>
              </h2>

              <div className="space-y-3">
                {filteredStages.map((stage, index) => {
                  const IconComponent = stage.icon;
                  const isSelected = selectedStage?.id === stage.id;

                  return (
                    <motion.div
                      key={stage.id}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.03 }}
                      onClick={() => setSelectedStage(stage)}
                      className={`
                        relative group p-4 rounded-2xl border cursor-pointer transition-all
                        ${isSelected
                           ? "bg-background border-primary-500 shadow-lg shadow-primary-500/10 ring-1 ring-primary-500/40"
                          : "bg-background/50 border-border-color hover:border-border-color hover:bg-background/80"
                        }
                      `}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-center gap-3.5">
                          <div className={`p-2.5 rounded-xl bg-gradient-to-br ${stage.color} text-white shadow-md shrink-0`}>
                            <IconComponent className="w-4 h-4" />
                          </div>
                          <div>
                            <span className="text-[10px] font-extrabold uppercase tracking-wider text-primary-400 block">
                              Stage {stage.stageNum} of 14
                            </span>
                            <h3 className="text-sm font-extrabold text-text-primary group-hover:text-primary-300 transition-colors">
                              {stage.name}
                            </h3>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono px-2 py-0.5 bg-surface-muted text-text-muted rounded border border-border-color">
                            {stage.tech[0]}
                          </span>
                          <ArrowRight className={`w-4 h-4 transition-transform ${isSelected ? "text-primary-400 translate-x-1" : "text-text-secondary group-hover:text-text-muted"}`} />
                        </div>
                      </div>

                      <p className="text-xs text-text-muted mt-2 line-clamp-2 leading-relaxed">
                        {stage.description}
                      </p>
                    </motion.div>
                  );
                })}
              </div>
            </div>

            {/* Inspector Panel (5 Cols) */}
            <div className="lg:col-span-5">
              <div className="sticky top-6">
                <h2 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-2 mb-4">
                  <Info className="w-4 h-4 text-primary-400" />
                  <span>Pipeline Component Inspector</span>
                </h2>

                {selectedStage ? (
                  <motion.div
                    key={selectedStage.id}
                    initial={{ opacity: 0, scale: 0.97 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="bg-background border border-primary-500/40 premium-card rounded-2xl p-6 shadow-2xl space-y-6 relative overflow-hidden"
                  >
                    {/* Background Glow */}
                    <div
                      className="absolute -right-20 -top-20 w-56 h-56 rounded-full blur-3xl pointer-events-none"
                      style={{ background: selectedStage.bgGlow }}
                    />

                    <div className="flex items-center gap-3">
                      <div className={`p-3 rounded-2xl bg-gradient-to-br ${selectedStage.color} text-white shadow-lg`}>
                        {React.createElement(selectedStage.icon, { className: "w-6 h-6" })}
                      </div>
                      <div>
                        <span className="text-xs font-extrabold uppercase tracking-wider text-primary-400 block">
                          Stage {selectedStage.stageNum} of 14
                        </span>
                        <h3 className="text-xl font-extrabold text-text-primary">
                          {selectedStage.name}
                        </h3>
                      </div>
                    </div>

                    <div>
                      <h4 className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2">Architectural Summary</h4>
                      <p className="text-xs text-text-secondary leading-relaxed bg-background/60 p-3.5 rounded-xl border border-border-color/80">
                        {selectedStage.description}
                      </p>
                    </div>

                    <div>
                      <h4 className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2">Key Responsibilities</h4>
                      <ul className="space-y-2">
                        {selectedStage.keyFunctions.map((fn, i) => (
                          <li key={i} className="text-xs text-text-secondary flex items-center gap-2">
                            <CheckCircle2 className="w-4 h-4 text-success-400 shrink-0" />
                            <span>{fn}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <h4 className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2">Technology Stack</h4>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedStage.tech.map((t) => (
                          <span key={t} className="text-xs font-bold px-2.5 py-1 bg-primary-500/20 text-primary-300 rounded-lg border border-primary-500/30">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h4 className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2">Source Location</h4>
                      <code className="text-xs font-mono block p-3 bg-background text-primary-300 rounded-xl border border-border-color break-all">
                        {selectedStage.sourcePath}
                      </code>
                    </div>
                  </motion.div>
                ) : (
                  <div className="bg-background/40 border border-border-color rounded-2xl p-8 text-center text-text-muted text-xs premium-card">
                    Select any pipeline stage on the left to inspect architectural details.
                  </div>
                )}
              </div>
            </div>
          </div>
        </main>
  );
}
