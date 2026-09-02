"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  FileText,
  Database,
  MessageSquare,
  TrendingUp,
  Target,
  Clock,
  Star,
  Download,
  ExternalLink,
  X,
  Command,
} from "lucide-react";
import api from "@/lib/api";

const TABS = [
  { id: "all", label: "All", icon: Search },
  { id: "reports", label: "Reports", icon: FileText },
  { id: "workspaces", label: "Workspaces", icon: Database },
  { id: "datasets", label: "Datasets", icon: Database },
  { id: "conversations", label: "Conversations", icon: MessageSquare },
  { id: "forecasts", label: "Forecasts", icon: TrendingUp },
  { id: "recommendations", label: "Recommendations", icon: Target },
];

interface SearchResult {
  id: string;
  type: string;
  title: string;
  description: string;
  metadata: Record<string, string>;
  relevance: number;
  href: string;
  timestamp?: string;
  favorite?: boolean;
}

function SearchSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-surface rounded-2xl border border-border-color p-5 animate-pulse space-y-3">
          <div className="h-4 bg-border-color rounded w-3/4"></div>
          <div className="h-3 bg-surface-muted rounded w-full"></div>
          <div className="h-3 bg-surface-muted rounded w-5/6"></div>
          <div className="flex gap-2">
            <div className="h-6 bg-surface-muted rounded-lg w-20"></div>
            <div className="h-6 bg-surface-muted rounded-lg w-20"></div>
          </div>
        </div>
      ))}
    </div>
  );
}

function ResultCard({ result, onFavorite }: { result: SearchResult; onFavorite: (id: string) => void }) {
  const iconMap: Record<string, React.ReactNode> = {
    reports: <FileText className="w-5 h-5 text-primary-600" />,
    workspaces: <Database className="w-5 h-5 text-primary-600" />,
    datasets: <Database className="w-5 h-5 text-primary-600" />,
    conversations: <MessageSquare className="w-5 h-5 text-primary-600" />,
    forecasts: <TrendingUp className="w-5 h-5 text-primary-600" />,
    recommendations: <Target className="w-5 h-5 text-primary-600" />,
  };

  const colorMap: Record<string, string> = {
    reports: "bg-primary-50 border-primary-100",
    workspaces: "bg-primary-50 border-primary-100",
    datasets: "bg-primary-50 border-primary-100",
    conversations: "bg-primary-50 border-primary-100",
    forecasts: "bg-success-50 border-success-100",
    recommendations: "bg-warning-50 border-warning-100",
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface rounded-2xl border border-border-color p-5 shadow-sm hover:shadow-md hover:border-primary-200 transition-all group"
    >
      <div className="flex items-start gap-4">
        <div className={`p-3 rounded-xl border ${colorMap[result.type] || colorMap.reports}`}>
          {iconMap[result.type] || iconMap.reports}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-text-primary truncate group-hover:text-primary-700 transition-colors">
              {result.title}
            </h3>
            <div className="flex items-center gap-1 flex-shrink-0">
              <button
                onClick={() => onFavorite(result.id)}
                className={`p-1 rounded-lg transition-colors ${
                  result.favorite ? "text-warning-500 bg-warning-50" : "text-text-muted hover:text-text-secondary hover:bg-surface-muted"
                }`}
              >
                <Star className={`w-4 h-4 ${result.favorite ? "fill-current" : ""}`} />
              </button>
              <span className="text-[10px] font-mono font-bold text-text-muted bg-surface-muted px-2 py-0.5 rounded">
                {Math.round(result.relevance * 100)}%
              </span>
            </div>
          </div>
          <p className="text-xs text-text-muted mt-1 leading-relaxed line-clamp-2">{result.description}</p>
          <div className="flex flex-wrap items-center gap-2 mt-3">
            {Object.entries(result.metadata).map(([key, value]) => (
              <span key={key} className="text-[10px] px-2 py-0.5 bg-surface-muted text-text-secondary rounded-lg font-medium">
                {key}: {value}
              </span>
            ))}
            {result.timestamp && (
              <span className="text-[10px] px-2 py-0.5 bg-surface-muted text-text-secondary rounded-lg font-medium flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(result.timestamp).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-border-light">
        <a
          href={result.href}
          className="text-[11px] px-3 py-1.5 bg-primary-600 text-white rounded-xl font-semibold hover:bg-primary-700 transition flex items-center gap-1"
        >
          <ExternalLink className="w-3 h-3" />
          Open
        </a>
        <button className="text-[11px] px-3 py-1.5 bg-surface-muted text-text-primary rounded-xl font-semibold hover:bg-border-color transition flex items-center gap-1">
          <Download className="w-3 h-3" />
          Save
        </button>
      </div>
    </motion.div>
  );
}

function SearchEmptyState({ query }: { query: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] text-center space-y-4">
      <div className="p-5 bg-surface-muted text-text-muted rounded-2xl border border-border-color">
        <Search className="w-10 h-10" />
      </div>
      <div>
        <h2 className="text-lg font-bold text-text-primary">No Results Found</h2>
        <p className="text-sm text-text-muted mt-1 max-w-md">
          {query
            ? `We couldn't find anything matching "${query}". Try different keywords or browse categories.`
            : "Start typing to search across reports, workspaces, datasets, and more."}
        </p>
      </div>
    </div>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState("all");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [recentSearches, setRecentSearches] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const stored = localStorage.getItem("search_recent");
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });
  const [favorites, setFavorites] = useState<Record<string, boolean>>({});

  const performSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const res = await api.get("/search", { params: { q, limit: 20 } });
      if (res.data) {
        const json = res.data;
        const items = (json.results || json.items || []).map((item: Record<string, unknown>) => ({
          id: (item.id as string) || `${item.type as string}-${Math.random()}`,
          type: (item.type as string) || "reports",
          title: (item.title as string) || (item.name as string) || "Untitled",
          description: (item.description as string) || (item.summary as string) || "",
          metadata: (item.metadata as Record<string, string>) || {},
          relevance: (item.relevance as number) || (item.score as number) || 0.8,
          href: (item.href as string) || (item.url as string) || "#",
          timestamp: (item.timestamp as string) || (item.created_at as string),
          favorite: favorites[(item.id as string) || ""],
        }));
        setResults(items);
      } else {
        setResults([]);
      }
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [favorites]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (query.trim()) {
        performSearch(query);
        setRecentSearches((prev) => {
          const next = [query, ...prev.filter((s) => s !== query)].slice(0, 10);
          localStorage.setItem("search_recent", JSON.stringify(next));
          return next;
        });
      } else {
        setResults([]);
      }
    }, 300);
    return () => clearTimeout(timeout);
  }, [query, performSearch]);

  const filteredResults = useMemo(() => {
    if (activeTab === "all") return results;
    return results.filter((r) => r.type === activeTab.slice(0, -1) || (activeTab === "all" && true));
  }, [results, activeTab]);

  const toggleFavorite = (id: string) => {
    setFavorites((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      localStorage.setItem("search_favorites", JSON.stringify(next));
      return next;
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      (document.querySelector(".search-input") as HTMLInputElement)?.focus();
    }
  };

  return (
    <div className="py-6 sm:py-8 space-y-6">
      {/* Search Header */}
      <div className="bg-surface premium-card border border-border-color shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-bold text-text-primary">Global Search</h1>
          <span className="text-[10px] font-mono text-text-muted bg-surface-muted px-2 py-1 rounded-lg border border-border-color flex items-center gap-1">
            <Command className="w-3 h-3" aria-hidden="true" /> Cmd+K
          </span>
        </div>
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" aria-hidden="true" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search reports, workspaces, datasets, forecasts..."
            aria-label="Search reports, workspaces, datasets, forecasts"
            className="search-input w-full pl-12 pr-4 py-4 text-sm border border-border-color rounded-2xl outline-none focus:border-primary-600 bg-surface-muted focus:bg-surface transition shadow-sm"
            autoFocus
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 rounded p-1"
              aria-label="Clear search input"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          )}
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
                  activeTab === tab.id
                    ? "bg-primary-600 text-white shadow-md"
                    : "text-text-secondary hover:bg-surface-muted"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Recent Searches */}
      {!query && recentSearches.length > 0 && (
        <div className="bg-surface premium-card border border-border-color shadow-sm p-6 space-y-3">
          <h2 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 text-text-muted" />
            Recent Searches
          </h2>
          <div className="flex flex-wrap gap-2">
            {recentSearches.map((s) => (
              <button
                key={s}
                onClick={() => setQuery(s)}
                className="text-xs px-3 py-1.5 bg-surface-muted text-text-primary rounded-xl hover:bg-primary-50 hover:text-primary-700 transition flex items-center gap-1.5"
              >
                <Search className="w-3 h-3" />
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      <div>
        {loading ? (
          <SearchSkeleton />
        ) : filteredResults.length === 0 ? (
          query ? <SearchEmptyState query={query} /> : null
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-text-muted font-medium">
              {filteredResults.length} result{filteredResults.length !== 1 ? "s" : ""} for &quot;{query}&quot;
            </p>
            <AnimatePresence>
              {filteredResults.map((result) => (
                <ResultCard key={result.id} result={result} onFavorite={toggleFavorite} />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}
