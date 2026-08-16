"use client";

import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import UploadCard from "@/components/upload/UploadCard";
import WorkspaceUploadWizard from "@/components/upload/WorkspaceUploadWizard";
import Link from "next/link";
import { motion } from "framer-motion";
import { LayoutDashboard, UploadCloud, Database, Sparkles, CheckCircle2, Layers, ArrowRight } from "lucide-react";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
};

export default function UploadPage() {
  return (
    <motion.div
      className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Header Banner */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="premium-card p-5 lg:p-6 flex flex-col md:flex-row md:items-center justify-between gap-4"
      >
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600 mb-1">
            <UploadCloud className="w-4 h-4" /> Data Ingestion Portal
          </div>
          <h1 className="text-2xl font-extrabold text-text-primary">
            Upload Business Data
          </h1>
          <p className="text-sm text-text-muted mt-1">
            Upload CSV, Excel, Parquet, or ZIP archives to create your business workspace. DecisionLens will automatically analyze relationships and generate AI insights.
          </p>
        </div>

        <Link
          href="/dynamic-dashboard"
          className="px-5 py-2.5 bg-background hover:bg-surface-muted text-text-primary text-xs font-semibold rounded-xl transition-colors flex items-center gap-2"
        >
          <LayoutDashboard className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </Link>
      </motion.div>

      {/* Main Upload Area */}
      <WorkspaceUploadWizard />

      {/* Secondary Upload */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.4 }}
        className="max-w-4xl mx-auto space-y-3"
      >
        <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">Single File Upload</h3>
        <UploadCard />
      </motion.div>

      {/* What Happens Next */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto"
      >
        {[
          {
            icon: Layers,
            color: "bg-primary-50 text-primary-600",
            title: "Automatic Relationship Detection",
            desc: "We detect primary keys, foreign keys, and relationships between your tables automatically.",
          },
          {
            icon: Sparkles,
            color: "bg-success-50 text-success-600",
            title: "AI-Powered Analysis",
            desc: "Our AI classifies your data into meaningful business categories and generates insights.",
          },
          {
            icon: CheckCircle2,
            color: "bg-primary-50 text-primary-600",
            title: "Instant Dashboard",
            desc: "Get a complete executive dashboard with KPIs, trends, and recommendations immediately.",
          },
        ].map((item, idx) => (
          <motion.div
            key={idx}
            variants={itemVariants}
            whileHover={{ y: -3, transition: { duration: 0.2 } }}
             className="premium-card p-5 space-y-2"
          >
            <div className={`p-2.5 ${item.color} rounded-xl w-fit`}>
              <item.icon className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-text-primary">{item.title}</h3>
            <p className="text-xs text-text-muted">{item.desc}</p>
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  );
}
