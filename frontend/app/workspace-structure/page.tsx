"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import LoadingSpinner from "@/components/ui/LoadingSpinner";
import ErrorState from "@/components/ui/ErrorState";
import {
  Layers,
  Database,
  GitMerge,
  Table,
  CheckCircle2,
  AlertTriangle,
  Info,
  ArrowRight,
  Sparkles,
  RefreshCw,
  FolderArchive,
  BookOpen
} from "lucide-react";

interface TableMeta {
  table_name: string;
  file_name?: string;
  row_count: number;
  columns: any[];
  role: string;
  is_fact?: boolean;
  reason?: string;
  description?: string;
}

interface Relationship {
  from_table: string;
  from_column: string;
  to_table: string;
  to_column: string;
  cardinality: string;
  confidence_score: number;
  status: string;
}

interface ColumnIntelligence {
  name: string;
  data_type: string;
  semantic_type: string;
  business_role: string;
  is_measure: boolean;
  is_dimension: boolean;
  is_temporal: boolean;
  is_identifier: boolean;
  confidence: number;
}

interface IntelligenceProfile {
  detected_domain: string;
  confidence_pct: number;
  detected_entities: string[];
  detected_measures: string[];
  detected_dimensions: string[];
  detected_temporal: string[];
  total_records: number;
  total_columns: number;
}

interface DataQualityIntelligence {
  overall_score: number;
  completeness: number;
  uniqueness: number;
  consistency: number;
  validity: number;
  accuracy: number;
  null_percentage: number;
  issues: string[];
}

interface DatasetIntelligence {
  workspace_id: string;
  status: string;
  domain: string;
  domain_confidence: number;
  domain_reason: string;
  dataset_type: string;
  generated_at: string;
  columns: ColumnIntelligence[];
  data_quality: DataQualityIntelligence;
  profile: IntelligenceProfile;
}

interface WorkspaceStructure {
  status: string;
  is_lookup_only: boolean;
  primary_fact_table: string | null;
  active_joins_count: number;
  unified_row_count: number;
  fact_tables: TableMeta[];
  dimension_tables: TableMeta[];
  lookup_tables: TableMeta[];
  reference_tables: TableMeta[];
  relationships: Relationship[];
  workspace_id?: string;
}

export default function WorkspaceStructurePage() {
  const [data, setData] = useState<WorkspaceStructure | null>(null);
  const [intelligence, setIntelligence] = useState<DatasetIntelligence | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStructure();
  }, []);

  useEffect(() => {
    if (data?.workspace_id) {
      fetchIntelligence();
    }
  }, [data]);

  async function fetchStructure() {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get("/workspace/structure");
      setData(res.data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load workspace structure. Please check your connection.";
      setError(message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  async function fetchIntelligence() {
    try {
      const wsId = data?.workspace_id || await getActiveWorkspaceId();
      if (!wsId) return;
      const res = await api.get(`/intelligence/workspace/${wsId}`);
      setIntelligence(res.data);
    } catch (err) {
      console.error("[WorkspaceStructure] Failed to load intelligence:", err);
      setIntelligence(null);
    }
  }

  async function getActiveWorkspaceId(): Promise<string | null> {
    try {
      const res = await api.get("/workspace/active");
      return res.data?.workspace_id || null;
    } catch {
      return null;
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <LoadingSpinner label="Loading workspace structure..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[70vh]">
        <ErrorState title="Failed to load workspace structure" description={error} onRetry={fetchStructure} retryLabel="Retry" />
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
       {/* Header Banner */}
       <div className="bg-background text-text-primary p-8 rounded-2xl shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-6 border border-border-color premium-card">
        <div>
          <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-widest text-primary-400 mb-1">
            <Layers className="w-4 h-4" /> Workspace Structure
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight">Semantic Model</h1>
          <p className="text-sm text-text-muted max-w-2xl mt-1 leading-relaxed">
            View your workspace table relationships and data structure.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchStructure}
            className="px-4 py-2.5 bg-surface/10 hover:bg-surface/20 text-text-primary text-xs font-bold rounded-xl transition-all border border-border-color/60 flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Dataset Intelligence Profile */}
      {intelligence && (
        <div className="bg-surface p-6 rounded-2xl border border-border-color shadow-sm space-y-4 premium-card">
          <div className="flex items-center justify-between border-b border-border-light pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary-600" />
              <h2 className="text-lg font-bold text-text-primary">Dataset Intelligence Profile</h2>
            </div>
            <span className="text-xs font-mono bg-primary-50 text-primary-700 px-3 py-1 rounded-full font-bold">
              {intelligence.status}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 bg-surface-muted rounded-2xl border border-border-color space-y-1 premium-card">
              <span className="text-xs text-text-muted font-medium block">Detected Domain</span>
              <div className="text-lg font-extrabold text-text-primary">{intelligence.domain}</div>
              <span className="text-[11px] text-text-muted block font-mono">
                Confidence: {intelligence.domain_confidence.toFixed(1)}%
              </span>
            </div>

            <div className="p-4 bg-surface-muted rounded-2xl border border-border-color space-y-1 premium-card">
              <span className="text-xs text-text-muted font-medium block">Dataset Type</span>
              <div className="text-lg font-extrabold text-text-primary">{intelligence.dataset_type}</div>
              <span className="text-[11px] text-text-muted block font-mono">
                {intelligence.profile.total_records?.toLocaleString() || "0"} records
              </span>
            </div>

            <div className="p-4 bg-surface-muted rounded-2xl border border-border-color space-y-1 premium-card">
              <span className="text-xs text-text-muted font-medium block">Dataset Health</span>
              <div className="text-lg font-extrabold text-text-primary">
                {intelligence.data_quality?.overall_score?.toFixed(1) || "N/A"}/100
              </div>
              <span className="text-[11px] text-text-muted block font-mono">
                {intelligence.data_quality?.issues?.length || 0} issues
              </span>
            </div>

            <div className="p-4 bg-surface-muted rounded-2xl border border-border-color space-y-1 premium-card">
              <span className="text-xs text-text-muted font-medium block">Semantic Confidence</span>
              <div className="text-lg font-extrabold text-text-primary">
                {intelligence.domain_confidence.toFixed(1)}%
              </div>
              <span className="text-[11px] text-text-muted block font-mono">
                {intelligence.profile.total_columns || 0} columns classified
              </span>
            </div>
          </div>

          {intelligence.profile?.detected_entities?.length > 0 && (
            <div className="p-4 bg-primary-50 rounded-2xl border border-primary-100">
              <div className="text-xs font-bold text-primary-700 mb-2">Detected Business Entities</div>
              <div className="flex flex-wrap gap-2">
                {intelligence.profile.detected_entities.map((entity: string, idx: number) => (
                  <span key={idx} className="px-2 py-1 bg-primary-100 text-primary-800 text-[10px] font-extrabold rounded-md">
                    {entity}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-success-50 rounded-2xl border border-success-100">
              <div className="text-xs font-bold text-success-700 mb-2">Detected Measures</div>
              <div className="text-sm font-extrabold text-success-800">
                {intelligence.profile?.detected_measures?.length || 0}
              </div>
              <div className="text-[11px] text-success-600 mt-1">
                {intelligence.profile?.detected_measures?.slice(0, 5).join(", ") || "None detected"}
              </div>
            </div>

            <div className="p-4 bg-teal-50 rounded-2xl border border-teal-100">
              <div className="text-xs font-bold text-teal-700 mb-2">Detected Dimensions</div>
              <div className="text-sm font-extrabold text-teal-900">
                {intelligence.profile?.detected_dimensions?.length || 0}
              </div>
              <div className="text-[11px] text-teal-600 mt-1">
                {intelligence.profile?.detected_dimensions?.slice(0, 5).join(", ") || "None detected"}
              </div>
            </div>

            <div className="p-4 bg-primary-50 rounded-2xl border border-primary-100">
              <div className="text-xs font-bold text-primary-700 mb-2">Date Columns</div>
              <div className="text-sm font-extrabold text-primary-800">
                {intelligence.profile?.detected_temporal?.length || 0}
              </div>
              <div className="text-[11px] text-primary-600 mt-1">
                {intelligence.profile?.detected_temporal?.slice(0, 5).join(", ") || "None detected"}
              </div>
            </div>
          </div>

          {intelligence.data_quality?.issues?.length > 0 && (
            <div className="p-4 bg-warning-50 rounded-2xl border border-warning-100">
              <div className="text-xs font-bold text-warning-700 mb-2">Data Quality Issues</div>
              <ul className="space-y-1">
                {intelligence.data_quality.issues.map((issue: string, idx: number) => (
                  <li key={idx} className="text-xs text-warning-800 flex items-center gap-2">
                    <AlertTriangle className="w-3 h-3 text-warning-600" />
                    {issue}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Overview Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-surface p-5 rounded-2xl border border-border-color shadow-sm space-y-1 premium-card">
          <span className="text-xs text-text-muted font-medium block">Primary Table</span>
          <div className="text-lg font-extrabold text-text-primary flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-success-500" />
            <span>{data?.primary_fact_table || "Unified Star Schema"}</span>
          </div>
          <span className="text-[11px] text-text-muted block font-mono">
            Unified Rows: {data?.unified_row_count?.toLocaleString() || "0"}
          </span>
        </div>

        <div className="bg-surface p-5 rounded-2xl border border-border-color shadow-sm space-y-1 premium-card">
          <span className="text-xs text-text-muted font-medium block">Fact Tables</span>
          <div className="text-2xl font-extrabold text-primary-600">
            {data?.fact_tables?.length || 0}
          </div>
          <span className="text-[11px] text-text-muted block font-mono">Core Data</span>
        </div>

        <div className="bg-surface p-5 rounded-2xl border border-border-color shadow-sm space-y-1 premium-card">
          <span className="text-xs text-text-muted font-medium block">Dimension Tables</span>
          <div className="text-2xl font-extrabold text-teal-600">
            {(data?.dimension_tables?.length || 0) + (data?.lookup_tables?.length || 0)}
          </div>
          <span className="text-[11px] text-text-muted block font-mono">Supporting Data</span>
        </div>

        <div className="bg-surface p-5 rounded-2xl border border-border-color shadow-sm space-y-1 premium-card">
          <span className="text-xs text-text-muted font-medium block">Active Relationships</span>
          <div className="text-2xl font-extrabold text-primary-600">
            {data?.active_joins_count || data?.relationships?.length || 0}
          </div>
          <span className="text-[11px] text-text-muted block font-mono">Auto-Detected</span>
        </div>
      </div>

      {/* Lookup Only Notice */}
      {data?.is_lookup_only && (
        <div className="bg-warning-50 rounded-2xl p-6 border border-warning-200 text-warning-800 space-y-3 premium-card">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-warning-600" />
            <h3 className="text-lg font-bold">Reference Dataset Uploaded</h3>
          </div>
          <p className="text-xs text-warning-800 leading-relaxed max-w-3xl">
            The active file is a reference/lookup table. It enriches operational datasets but cannot drive executive KPIs by itself.
          </p>
          <div className="pt-2">
            <Link
              href="/upload"
              className="px-4 py-2 bg-warning-600 hover:bg-warning-700 text-white text-xs font-bold rounded-xl transition-all shadow-md inline-flex items-center gap-2"
            >
              <FolderArchive className="w-4 h-4" />
              <span>Upload Transactional Dataset</span>
            </Link>
          </div>
        </div>
      )}

      {/* Section 1: Fact Tables */}
      <div className="bg-surface p-6 rounded-2xl border border-border-color shadow-sm space-y-4 premium-card">
        <div className="flex items-center justify-between border-b border-border-light pb-3">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-primary-600" />
            <h2 className="text-lg font-bold text-text-primary">Primary Fact Tables</h2>
          </div>
          <span className="text-xs font-mono bg-primary-50 text-primary-700 px-3 py-1 rounded-full font-bold">
            {data?.fact_tables?.length || 0} Fact Tables
          </span>
        </div>

        {data?.fact_tables && data.fact_tables.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.fact_tables.map((t, idx) => (
              <div key={idx} className="p-4 bg-surface-muted rounded-2xl border border-border-color space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-primary-600 uppercase tracking-wider">
                    Fact Table
                  </span>
                  <span className="text-[11px] bg-primary-100 text-primary-800 px-2 py-0.5 rounded-md font-bold">
                    {t.row_count?.toLocaleString()} rows
                  </span>
                </div>
                <h3 className="text-sm font-bold text-text-primary">{t.table_name}</h3>
                <p className="text-xs text-text-muted leading-relaxed">{t.reason || t.description}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-muted italic">No fact tables detected.</p>
        )}
      </div>

      {/* Section 2: Dimension & Lookup Tables */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Dimension Tables */}
        <div className="bg-surface p-6 rounded-2xl border border-border-color shadow-sm space-y-4 premium-card">
          <div className="flex items-center justify-between border-b border-border-light pb-3">
            <div className="flex items-center gap-2">
              <Table className="w-5 h-5 text-teal-600" />
              <h2 className="text-base font-bold text-text-primary">Dimension Tables</h2>
            </div>
            <span className="text-xs font-mono bg-teal-50 text-teal-700 px-2.5 py-0.5 rounded-full font-bold">
              {data?.dimension_tables?.length || 0} Tables
            </span>
          </div>

          <div className="space-y-3">
            {data?.dimension_tables && data.dimension_tables.length > 0 ? (
              data.dimension_tables.map((t, idx) => (
                <div key={idx} className="p-3 bg-surface-muted rounded-xl border border-border-color flex items-center justify-between text-xs">
                  <div>
                    <strong className="font-bold text-text-primary block">{t.table_name}</strong>
                    <span className="text-[11px] text-text-muted">{t.description}</span>
                  </div>
                  <span className="font-mono text-text-muted">{t.row_count?.toLocaleString()} rows</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-text-muted italic">No dimension tables.</p>
            )}
          </div>
        </div>

        {/* Lookup Tables */}
        <div className="bg-surface p-6 rounded-2xl border border-border-color shadow-sm space-y-4 premium-card">
          <div className="flex items-center justify-between border-b border-border-light pb-3">
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary-600" />
              <h2 className="text-base font-bold text-text-primary">Lookup & Reference Tables</h2>
            </div>
            <span className="text-xs font-mono bg-primary-50 text-primary-700 px-2.5 py-0.5 rounded-full font-bold">
              {(data?.lookup_tables?.length || 0) + (data?.reference_tables?.length || 0)} Tables
            </span>
          </div>

          <div className="space-y-3">
            {((data?.lookup_tables || []).concat(data?.reference_tables || [])).length > 0 ? (
              (data?.lookup_tables || []).concat(data?.reference_tables || []).map((t, idx) => (
                <div key={idx} className="p-3 bg-primary-50/40 rounded-xl border border-primary-200/60 flex items-center justify-between text-xs">
                  <div>
                    <div className="flex items-center gap-2">
                      <strong className="font-bold text-text-primary">{t.table_name}</strong>
                      <span className="px-2 py-0.5 bg-primary-100 text-primary-800 text-[10px] font-extrabold rounded">
                        Lookup
                      </span>
                    </div>
                    <span className="text-[11px] text-text-muted mt-0.5 block">Enriches data via joins</span>
                  </div>
                  <span className="font-mono text-primary-700 font-bold">{t.row_count?.toLocaleString()} rows</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-text-muted italic">No lookup tables.</p>
            )}
          </div>
        </div>
      </div>

      {/* Section 3: PK/FK Relationship Graph */}
      <div className="bg-surface p-6 rounded-2xl border border-border-color shadow-sm space-y-4 premium-card">
        <div className="flex items-center justify-between border-b border-border-light pb-3">
          <div className="flex items-center gap-2">
            <GitMerge className="w-5 h-5 text-primary-600" />
            <h2 className="text-lg font-bold text-text-primary">Relationship Graph</h2>
          </div>
          <span className="text-xs font-mono bg-success-50 text-success-700 px-3 py-1 rounded-full font-bold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> Connected Schema
          </span>
        </div>

        {data?.relationships && data.relationships.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            {data.relationships.map((rel, idx) => (
              <div key={idx} className="p-3.5 bg-surface-muted rounded-xl border border-border-color flex items-center justify-between">
                <div className="flex items-center gap-2 font-mono">
                  <span className="font-bold text-primary-700">{rel.from_table}.{rel.from_column}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-text-muted" />
                  <span className="font-bold text-teal-700">{rel.to_table}.{rel.to_column}</span>
                </div>
                <span className="px-2 py-0.5 bg-success-100 text-success-800 text-[10px] font-extrabold rounded-md">
                  {rel.cardinality || "1:N"} ({rel.confidence_score || 95}%)
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-text-muted italic">No relationships detected.</p>
        )}
      </div>
    </div>
  );
}
