"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useToast } from "@/lib/toast";
import api from "@/lib/api";
import {
  Database,
  Search,
  FolderOpen,
  Table2,
  BookOpen,
  FileJson,
  RefreshCw,
  ArrowRight,
  Filter,
  ChevronDown,
  ChevronRight,
  Hash,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

interface CatalogColumn {
  name: string;
  type: string;
  null_percentage: number;
  unique_values: number;
  category: string;
}

interface CatalogTable {
  name: string;
  schema_name?: string;
  columns?: CatalogColumn[];
  row_count?: number;
  description?: string;
  domain?: string;
  updated_at?: string;
  tags?: string[];
  table_role?: string;
  columns_count?: number;
  column_count?: number;
  record_count?: number;
  profile_summary?: {
    total_rows?: number;
    total_columns?: number;
    measures?: string[];
    dimensions?: string[];
    entities?: string[];
  };
}

interface GlossaryTerm {
  term: string;
  definition: string;
  domain?: string;
}

const DOMAIN_COLORS: Record<string, string> = {
  Retail: "bg-success-100 text-success-700 border-success-200",
  Finance: "bg-info-100 text-info-700 border-info-200",
  Healthcare: "bg-error-100 text-error-700 border-error-200",
  HR: "bg-primary-100 text-primary-700 border-primary-200",
  Marketing: "bg-warning-100 text-warning-700 border-warning-200",
  Education: "bg-primary-100 text-primary-700 border-primary-200",
  Cybersecurity: "bg-error-100 text-error-700 border-error-200",
  General: "bg-surface-muted text-text-secondary border-border-color",
  Logistics: "bg-warning-100 text-warning-700 border-warning-200",
  Manufacturing: "bg-warning-100 text-warning-700 border-warning-200",
  Telecom: "bg-info-100 text-info-700 border-info-200",
  Insurance: "bg-success-100 text-success-700 border-success-200",
  SaaS: "bg-primary-100 text-primary-700 border-primary-200",
  CRM: "bg-primary-100 text-primary-700 border-primary-200",
  Government: "bg-surface-muted text-text-secondary border-border-color",
  RealEstate: "bg-success-100 text-success-700 border-success-200",
  Hospitality: "bg-error-100 text-error-700 border-error-200",
  Agriculture: "bg-success-100 text-success-700 border-success-200",
  Energy: "bg-info-100 text-info-700 border-info-200",
};

export default function DataCatalogPage() {
  const [tables, setTables] = useState<CatalogTable[]>([]);
  const [glossary, setGlossary] = useState<GlossaryTerm[]>([]);
  const [search, setSearch] = useState("");
  const [domainFilter, setDomainFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"tables" | "glossary">("tables");
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());
  const [showColumnsOnly, setShowColumnsOnly] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    fetchCatalogData();
  }, []);

  async function fetchCatalogData() {
    try {
      setLoading(true);
      setLoadError(null);
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (domainFilter && domainFilter !== "all") params.set("domain", domainFilter);

      const [tablesRes, glossaryRes] = await Promise.all([
        api.get("/catalog/tables", { params }),
        api.get("/catalog/glossary"),
      ]);

      const tablesData = tablesRes.data;
      const rawTables = Array.isArray(tablesData) ? tablesData : (tablesData.tables || []);
      const normalized = rawTables.map((t: any) => ({
        ...t,
        columns: Array.isArray(t.columns) ? t.columns : [],
        row_count: t.row_count ?? t.record_count,
        column_count: t.column_count ?? t.columns_count ?? (t.columns?.length || 0),
        description: t.description || t.business_description || "",
        domain: t.domain || t.business_domain || "General",
      }));
      setTables(normalized);
      if (rawTables.length > 0 && tables.length === 0) {
        addToast({ type: "info", title: "Catalog loaded", description: `${normalized.length} tables found.` });
      }
      const gData = glossaryRes.data;
      setGlossary(gData.terms || []);
    } catch (err) {
      console.error("[Catalog] Failed to load data:", err);
      setLoadError("Failed to load catalog data. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  const filteredTables = tables.filter((t) => {
    const matchesSearch =
      !search ||
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      (t.description || "").toLowerCase().includes(search.toLowerCase()) ||
      (t.tags || []).some((tag) => tag.toLowerCase().includes(search.toLowerCase())) ||
      (t.columns || []).some((col) => col.name.toLowerCase().includes(search.toLowerCase()));
    const matchesDomain = domainFilter === "all" || (t.domain || "").toLowerCase() === domainFilter.toLowerCase();
    return matchesSearch && matchesDomain;
  });

  const domains = [...new Set(tables.map((t) => t.domain).filter(Boolean))];

  const toggleExpanded = (name: string) => {
    setExpandedTables((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const getDomainBadgeClass = (domain?: string) => {
    if (!domain) return DOMAIN_COLORS.General;
    const key = domain.replace(/[&\s]+/g, "");
    return DOMAIN_COLORS[domain] || DOMAIN_COLORS[key] || DOMAIN_COLORS.General;
  };

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-extrabold uppercase tracking-widest text-primary-600 mb-1">
            <Database className="w-4 h-4" /> Data Catalog
          </div>
          <h1 className="text-2xl font-extrabold text-text-primary">Enterprise Data Catalog</h1>
          <p className="text-sm text-text-muted mt-1 font-medium">
            Browse and search all datasets across your workspaces
          </p>
        </div>
        <button
          onClick={fetchCatalogData}
          className="px-4 py-2 bg-background hover:bg-surface-muted text-text-primary text-xs font-bold rounded-xl transition-all flex items-center gap-2"
          aria-label="Refresh catalog data"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      <div className="flex items-center gap-1 bg-surface rounded-xl border border-border-color p-1 w-fit" role="tablist" aria-label="Catalog views">
        <button
          onClick={() => setActiveTab("tables")}
          role="tab"
          aria-selected={activeTab === "tables"}
          className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-2 ${
            activeTab === "tables"
              ? "bg-primary-600 text-white shadow-sm"
              : "text-text-secondary hover:bg-surface-muted"
          }`}
        >
          <Table2 className="w-3.5 h-3.5" /> Tables
        </button>
        <button
          onClick={() => setActiveTab("glossary")}
          role="tab"
          aria-selected={activeTab === "glossary"}
          className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all flex items-center gap-2 ${
            activeTab === "glossary"
              ? "bg-primary-600 text-white shadow-sm"
              : "text-text-secondary hover:bg-surface-muted"
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" /> Glossary
        </button>
      </div>

      {loadError && (
        <div className="bg-error-50 premium-card border border-error-200 rounded-2xl p-6 flex items-center gap-3 text-sm text-error-700" role="alert">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <div className="flex-1">
            <p className="font-semibold">Failed to load catalog data</p>
            <p className="text-xs text-error-600 mt-0.5">{loadError}</p>
          </div>
          <button
            onClick={fetchCatalogData}
            className="px-4 py-2 bg-error-100 hover:bg-error-200 text-error-700 text-xs font-bold rounded-xl transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {loading && !loadError && (
            <div className="bg-surface premium-card rounded-2xl border border-border-color p-12 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3 text-text-muted">
            <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-sm font-medium">Loading catalog data...</span>
          </div>
        </div>
      )}

      {activeTab === "tables" && !loading && !loadError && (
        <div className="space-y-4">
          <div className="bg-surface premium-card rounded-2xl border border-border-color p-4 flex flex-col md:flex-row md:items-center gap-4">
            <div className="flex-1 relative">
              <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
              <input
                type="text"
                placeholder="Search tables..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-surface-muted border border-border-color rounded-xl text-xs text-text-primary placeholder:text-text-muted outline-none focus:border-primary-500 transition-colors"
                aria-label="Search catalog tables"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-text-muted" aria-hidden="true" />
              <select
                value={domainFilter}
                onChange={(e) => setDomainFilter(e.target.value)}
                className="text-xs font-semibold text-text-primary bg-surface-muted border border-border-color rounded-xl px-3 py-2.5 outline-none cursor-pointer"
                aria-label="Filter by domain"
              >
                <option value="all">All Domains</option>
                {domains.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowColumnsOnly(!showColumnsOnly)}
                className={`text-xs font-semibold px-3 py-2.5 rounded-xl border transition-colors ${
                  showColumnsOnly
                    ? "bg-primary-50 border-primary-200 text-primary-700"
                    : "bg-surface-muted border-border-color text-text-secondary hover:bg-surface-muted"
                }`}
                aria-pressed={showColumnsOnly}
              >
                {showColumnsOnly ? "Hide Columns" : "Show Columns"}
              </button>
            </div>
          </div>

          {filteredTables.length === 0 ? (
            <div className="bg-surface premium-card rounded-2xl border border-border-color p-12 text-center">
              <FolderOpen className="w-12 h-12 text-text-muted mx-auto mb-3" aria-hidden="true" />
              <p className="text-sm text-text-muted font-medium">No tables found matching your search.</p>
              {search && (
                <button
                  onClick={() => { setSearch(""); setDomainFilter("all"); }}
                  className="mt-3 text-xs font-semibold text-primary-600 hover:text-primary-700 underline"
                >
                  Clear filters
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {filteredTables.map((table) => {
                const isExpanded = expandedTables.has(table.name);
                const domainBadge = getDomainBadgeClass(table.domain);
                const cols = table.columns || [];
                const showTableCols = showColumnsOnly || isExpanded;

                return (
                  <div
                    key={table.name}
                     className="bg-surface premium-card rounded-2xl border border-border-color hover:border-primary-300 hover:shadow-md transition-all"
                  >
                    <div className="p-5">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="p-2.5 bg-primary-50 rounded-xl text-primary-600" aria-hidden="true">
                            <Table2 className="w-5 h-5" />
                          </div>
                          <div>
                            <h3 className="text-sm font-bold text-text-primary">{table.name}</h3>
                            <div className="flex items-center gap-2 mt-1">
                              {table.domain && (
                                <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md border ${domainBadge}`}>
                                  {table.domain}
                                </span>
                              )}
                              {table.table_role && (
                                <span className="text-[10px] font-mono font-medium text-text-muted bg-surface-muted px-2 py-0.5 rounded-md">
                                  {table.table_role}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {table.row_count !== undefined && (
                            <span className="text-[10px] font-mono font-bold text-text-muted bg-surface-muted px-2 py-1 rounded-lg">
                              {table.row_count.toLocaleString()} rows
                            </span>
                          )}
                        </div>
                      </div>

                      {table.description && (
                        <p className="text-xs text-text-muted mb-3 leading-relaxed">{table.description}</p>
                      )}

                      <div className="flex flex-wrap gap-1.5 mb-3">
                        {table.tags && table.tags.length > 0
                          ? table.tags.slice(0, 6).map((tag, ti) => (
                              <span
                                key={ti}
                                className="text-[10px] font-mono font-medium px-2 py-0.5 bg-primary-50 text-primary-600 rounded-md border border-primary-100"
                              >
                                {tag}
                              </span>
                            ))
                          : null}
                      </div>

                      <div className="flex items-center justify-between pt-3 border-t border-border-light">
                        <div className="flex items-center gap-3">
                          <span className="text-[10px] text-text-muted font-mono">
                            {table.updated_at ? new Date(table.updated_at).toLocaleDateString() : ""}
                          </span>
                          {cols.length > 0 && (
                            <span className="text-[10px] text-text-muted font-mono flex items-center gap-1">
                              <Hash className="w-3 h-3" /> {cols.length} columns
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => toggleExpanded(table.name)}
                            className="text-[10px] font-semibold text-primary-600 hover:text-primary-700 flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-primary-50 transition-colors"
                            aria-expanded={isExpanded}
                          >
                            {isExpanded ? (
                              <>
                                <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" /> Hide Columns
                              </>
                            ) : (
                              <>
                                <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" /> Show Columns
                              </>
                            )}
                          </button>
                          <ArrowRight className="w-3.5 h-3.5 text-text-muted" aria-hidden="true" />
                        </div>
                      </div>
                    </div>

                    {showTableCols && cols.length > 0 && (
                      <div className="border-t border-border-light bg-surface-muted/50">
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-xs">
                            <thead>
                              <tr className="bg-surface-muted text-text-muted">
                                <th className="px-5 py-2.5 font-semibold">Column</th>
                                <th className="px-5 py-2.5 font-semibold">Type</th>
                                <th className="px-5 py-2.5 font-semibold">Category</th>
                                <th className="px-5 py-2.5 font-semibold text-right">Null %</th>
                                <th className="px-5 py-2.5 font-semibold text-right">Unique</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200">
                              {cols.slice(0, showColumnsOnly ? undefined : 10).map((col, ci) => (
                                <tr key={ci} className="hover:bg-surface transition-colors">
                                  <td className="px-5 py-2 font-medium text-text-primary flex items-center gap-2">
                                    <span className="font-mono text-[11px]">{col.name}</span>
                                  </td>
                                  <td className="px-5 py-2">
                                    <span className="font-mono text-[10px] text-text-muted bg-surface border border-border-color px-2 py-0.5 rounded-md">
                                      {col.type}
                                    </span>
                                  </td>
                                  <td className="px-5 py-2">
                                    <span className="text-[10px] font-medium text-text-muted capitalize">
                                      {col.category}
                                    </span>
                                  </td>
                                  <td className="px-5 py-2 text-right">
                                    <span
                                      className={`text-[10px] font-mono font-medium ${
                                        col.null_percentage > 20
                                          ? "text-error-600"
                                          : col.null_percentage > 5
                                          ? "text-warning-600"
                                          : "text-success-600"
                                      }`}
                                    >
                                      {col.null_percentage.toFixed(1)}%
                                    </span>
                                  </td>
                                  <td className="px-5 py-2 text-right">
                                    <span className="text-[10px] font-mono text-text-muted">
                                      {col.unique_values !== undefined ? col.unique_values.toLocaleString() : "-"}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                              {!showColumnsOnly && cols.length > 10 && (
                                <tr>
                                  <td colSpan={5} className="px-5 py-2 text-center text-[10px] text-text-muted">
                                    +{cols.length - 10} more columns
                                  </td>
                                </tr>
                              )}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {activeTab === "glossary" && !loading && !loadError && (
        <div className="bg-surface premium-card rounded-2xl border border-border-color divide-y divide-slate-100">
          {glossary.length === 0 ? (
            <div className="p-12 text-center">
              <BookOpen className="w-12 h-12 text-text-muted mx-auto mb-3" aria-hidden="true" />
              <p className="text-sm text-text-muted font-medium">No glossary terms available.</p>
            </div>
          ) : (
            glossary.map((term, idx) => (
              <div key={idx} className="p-5 hover:bg-surface-muted transition-colors">
                <div className="flex items-center gap-2 mb-1">
                  <FileJson className="w-4 h-4 text-primary-500" aria-hidden="true" />
                  <h3 className="text-sm font-bold text-text-primary">{term.term}</h3>
                  {term.domain && (
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted bg-surface-muted px-2 py-0.5 rounded">
                      {term.domain}
                    </span>
                  )}
                </div>
                <p className="text-xs text-text-secondary leading-relaxed ml-6">{term.definition}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
