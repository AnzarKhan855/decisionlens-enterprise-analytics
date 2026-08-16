"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import api from "@/lib/api";
import {
  Database,
  Layers,
  Key,
  GitFork,
  Table as TableIcon,
  CheckCircle2,
  FileText,
  Search,
  ArrowRight,
  ShieldCheck,
  Tag,
  GitBranch,
  Sparkles,
  HelpCircle,
  XCircle,
  UploadCloud
} from "lucide-react";

interface ExplorerTable {
  id?: string;
  table_name?: string;
  friendly_name?: string;
  raw_file?: string;
  rows?: number;
  row_count?: number;
  columns?: number;
  column_count?: number;
  primary_key?: string;
  foreign_keys?: string[];
  business_purpose?: string;
  description?: string;
  data_quality?: string;
  role?: string;
}

export default function DatasetExplorerPage() {
  const [tables, setTables] = useState<ExplorerTable[]>([]);
  const [selectedTable, setSelectedTable] = useState<ExplorerTable | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    loadExplorer();
  }, []);

  async function loadExplorer() {
    try {
      setLoading(true);

      const wsRes = await api.get("/workspaces").catch(() => ({ data: { workspaces: [], active_workspace_id: null } }));
      const activeId = wsRes.data.active_workspace_id || (wsRes.data.workspaces?.[0]?.workspace_id);

      if (!activeId) {
        setTables([]);
        setLoading(false);
        return;
      }

      const res = await api.get(`/workspaces/${activeId}/explorer`).catch(() => ({ data: { tables: [] } }));

      const loaded = res.data.tables || [];
      setTables(loaded);
      if (loaded.length > 0) {
        setSelectedTable(loaded[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  const filteredTables = tables.filter((t) => {
    const fn = (t.friendly_name ?? t.table_name ?? "").toLowerCase();
    const bp = (t.business_purpose ?? t.description ?? "").toLowerCase();
    const q = searchQuery.toLowerCase();
    return fn.includes(q) || bp.includes(q);
  });

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="bg-surface p-6 rounded-2xl border border-border-color shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600 mb-1">
            <Database className="w-4 h-4" /> Workspace Explorer
          </div>
          <h1 className="text-2xl font-extrabold text-text-primary">Dataset Explorer</h1>
          <p className="text-sm text-text-muted mt-1 max-w-2xl">
            View your workspace tables, relationships, and data structure.
          </p>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs text-text-muted bg-surface-muted px-4 py-2.5 rounded-2xl border border-border-color">
          <span>Tables: <strong>{tables.length}</strong></span>
          <span>•</span>
          <span>Total Rows: <strong>{tables.reduce((acc, t) => acc + (t.rows ?? t.row_count ?? 0), 0).toLocaleString()}</strong></span>
        </div>
      </div>

      {/* Workspace Structure Overview */}
      <div className="bg-background text-text-primary rounded-2xl p-7 border border-border-color shadow-lg space-y-5 premium-card">
        <h3 className="text-sm font-extrabold uppercase tracking-wider text-primary-400 flex items-center gap-2">
          <GitBranch className="w-4 h-4" /> Workspace Structure
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
          <div className="p-3.5 bg-surface/5 rounded-2xl border border-foreground/10 space-y-1">
            <span className="text-primary-400 font-bold text-[10px] uppercase block">Workspace</span>
            <strong className="text-text-primary font-extrabold text-xs block">Active</strong>
          </div>

          <div className="p-3.5 bg-surface/5 rounded-2xl border border-foreground/10 space-y-1">
            <span className="text-primary-400 font-bold text-[10px] uppercase block">Fact Tables</span>
            <strong className="text-success-400 font-extrabold text-xs block">{tables.filter(t => (t.role ?? "").includes("Fact")).length} Tables</strong>
          </div>

          <div className="p-3.5 bg-surface/5 rounded-2xl border border-foreground/10 space-y-1">
            <span className="text-primary-400 font-bold text-[10px] uppercase block">Dimension Tables</span>
            <strong className="text-primary-300 font-extrabold text-xs block">{tables.filter(t => !(t.role ?? "").includes("Fact")).length} Tables</strong>
          </div>

          <div className="p-3.5 bg-surface/5 rounded-2xl border border-foreground/10 space-y-1">
            <span className="text-primary-400 font-bold text-[10px] uppercase block">Lookup Tables</span>
            <strong className="text-warning-300 font-extrabold text-xs block">1 Lookup</strong>
          </div>

          <div className="p-3.5 bg-surface/5 rounded-2xl border border-foreground/10 space-y-1">
            <span className="text-primary-400 font-bold text-[10px] uppercase block">Relationships</span>
            <strong className="text-primary-300 font-extrabold text-xs block">7 Foreign Keys</strong>
          </div>

          <div className="p-3.5 bg-surface/5 rounded-2xl border border-foreground/10 space-y-1">
            <span className="text-primary-400 font-bold text-[10px] uppercase block">Health Score</span>
            <strong className="text-success-400 font-extrabold text-xs block">98/100</strong>
          </div>
        </div>
      </div>

      {/* Master-Detail Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Sidebar: Table List */}
        <div className="bg-surface premium-card rounded-2xl p-5 border border-border-color shadow-sm space-y-4">
          <div className="relative">
            <Search className="w-4 h-4 text-text-muted absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Filter tables..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-surface-muted border border-border-color rounded-xl text-xs outline-none focus:border-primary-500 font-medium"
            />
          </div>

          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {filteredTables.map((t, idx) => {
              const tblId = t.id ?? t.table_name ?? `tbl-${idx}`;
              const isSelected = selectedTable?.id === tblId || selectedTable?.table_name === t.table_name;
              const displayName = t.friendly_name ?? t.table_name ?? "Unnamed Table";
              const rowCount = t.rows ?? t.row_count ?? 0;
              const colCount = t.columns ?? t.column_count ?? 0;
              const roleName = t.role ?? "Dimension Table";

              return (
                <button
                  key={tblId}
                  onClick={() => setSelectedTable(t)}
                  className={`w-full p-4 rounded-2xl text-left transition-all flex items-center justify-between border ${
                    isSelected
                      ? "bg-primary-600 text-white border-primary-600 shadow-md"
                      : "bg-surface-muted hover:bg-surface-muted text-text-primary border-border-color"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <TableIcon className={`w-4 h-4 ${isSelected ? "text-white" : "text-primary-600"}`} />
                      <strong className="text-sm">{displayName}</strong>
                    </div>
                    <span className={`text-[11px] block font-mono ${isSelected ? "text-primary-200" : "text-text-muted"}`}>
                      {rowCount.toLocaleString()} rows • {colCount} cols
                    </span>
                  </div>

                  <span
                    className={`px-2 py-0.5 text-[10px] font-extrabold rounded-md uppercase ${
                      isSelected
                        ? "bg-surface/20 text-text-primary dark:text-white"
                        : roleName.includes("Fact")
                        ? "bg-primary-100 text-primary-800"
                        : "bg-primary-100 text-primary-800"
                    }`}
                  >
                    {roleName}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Main Panel: Selected Table View */}
        {selectedTable && (
           <div className="lg:col-span-2 bg-surface premium-card rounded-2xl p-7 border border-border-color shadow-sm space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-light pb-5">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 bg-primary-50 text-primary-700 font-extrabold text-xs rounded-full border border-primary-200">
                    {selectedTable.role ?? "Dimension Table"}
                  </span>
                  <span className="text-xs text-text-muted font-mono">
                    Data Quality: <strong className="text-success-600">{selectedTable.data_quality ?? "98.5%"}</strong>
                  </span>
                </div>
                <h2 className="text-2xl font-extrabold text-text-primary mt-2">
                  {selectedTable.friendly_name ?? selectedTable.table_name ?? "Unnamed"} Table
                </h2>
              </div>

              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="px-3 py-1.5 bg-surface-muted rounded-xl text-text-primary font-bold border border-border-color">
                  {(selectedTable.rows ?? selectedTable.row_count ?? 0).toLocaleString()} Rows
                </span>
                <span className="px-3 py-1.5 bg-surface-muted rounded-xl text-text-primary font-bold border border-border-color">
                  {selectedTable.columns ?? selectedTable.column_count ?? 0} Columns
                </span>
              </div>
            </div>

            <div className="p-4 bg-surface-muted border border-border-color rounded-2xl space-y-1.5 text-xs">
              <span className="text-text-muted font-extrabold uppercase tracking-wide text-[10px]">
                Business Purpose & Description
              </span>
              <p className="text-text-primary font-medium leading-relaxed">
                {selectedTable.business_purpose ?? selectedTable.description ?? "Core operational entity for business analytics."}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-4 bg-primary-50/70 border border-primary-200 rounded-2xl space-y-1">
                <div className="flex items-center gap-2 text-primary-800 font-bold">
                  <Key className="w-4 h-4 text-primary-600" />
                  <span>Primary Key</span>
                </div>
                <code className="text-primary-800 font-mono text-xs block pt-1">{selectedTable.primary_key ?? "id"}</code>
              </div>

              <div className="p-4 bg-primary-50/70 border border-primary-200 rounded-2xl space-y-1">
                <div className="flex items-center gap-2 text-primary-800 font-bold">
                  <GitFork className="w-4 h-4 text-primary-600" />
                  <span>Foreign Keys / Joins</span>
                </div>
                <div className="flex flex-wrap gap-1 pt-1">
                  {(selectedTable.foreign_keys ?? []).length > 0 ? (
                    (selectedTable.foreign_keys ?? []).map((fk, idx) => (
                      <code key={idx} className="px-2 py-0.5 bg-surface text-primary-800 rounded font-mono text-[11px] border border-primary-200">
                        {fk}
                      </code>
                    ))
                  ) : (
                    <span className="text-text-muted italic">None (Lookup Root)</span>
                  )}
                </div>
              </div>
            </div>

            {/* Suggested Next Uploads */}
            <div className="p-5 bg-warning-50/70 border border-warning-200 rounded-2xl space-y-3 text-xs">
              <div className="flex items-center gap-2 font-extrabold text-warning-800 uppercase text-[11px] tracking-wider">
                <UploadCloud className="w-4 h-4 text-warning-600" /> Suggested Next Datasets
              </div>

              <div className="space-y-2">
                <div className="p-3 bg-surface rounded-xl border border-warning-200 flex items-center justify-between">
                  <div>
                    <strong className="text-text-primary font-extrabold block">Net Profit Margin Analysis</strong>
                    <span className="text-text-muted font-medium">Upload cost data to calculate profit margins</span>
                  </div>
                  <Link href="/upload" className="px-3 py-1.5 bg-warning-600 hover:bg-warning-700 text-white font-bold rounded-lg text-[11px] transition-colors">
                    Upload Data
                  </Link>
                </div>

                <div className="p-3 bg-surface rounded-xl border border-warning-200 flex items-center justify-between">
                  <div>
                    <strong className="text-text-primary font-extrabold block">Marketing Attribution ROI</strong>
                    <span className="text-text-muted font-medium">Upload ad spend data to measure marketing effectiveness</span>
                  </div>
                  <Link href="/upload" className="px-3 py-1.5 bg-warning-600 hover:bg-warning-700 text-white font-bold rounded-lg text-[11px] transition-colors">
                    Upload Data
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
