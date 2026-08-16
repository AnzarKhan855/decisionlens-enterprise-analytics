"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, X, ArrowRight, LayoutDashboard, Database, Building2, ShieldCheck, GitBranch, Bot, TrendingUp, LucideIcon } from "lucide-react";

interface SearchResult {
  title: string;
  category: string;
  url: string;
  icon: LucideIcon;
  description: string;
}

interface ExecutiveSearchModalProps {
  open?: boolean;
  onClose?: () => void;
}

const SEARCH_REGISTRY: SearchResult[] = [
  { title: "Executive Dashboard", category: "Dashboard", url: "/dynamic-dashboard", icon: LayoutDashboard, description: "Key metrics, trends, and AI-generated insights for your active dataset." },
  { title: "Executive Action Center", category: "Strategy", url: "/dynamic-dashboard", icon: TrendingUp, description: "Prioritized strategic recommendations with evidence and confidence scores." },
  { title: "Data Segmentation", category: "Analytics", url: "/dynamic-dashboard", icon: Building2, description: "Automated cohort and segment analysis across dataset dimensions." },
  { title: "Predictive Analytics", category: "Forecasting", url: "/dynamic-dashboard", icon: LayoutDashboard, description: "Time-series forecasts and prediction confidence intervals." },
  { title: "Data Quality & Trust", category: "Data Quality", url: "/data-quality", icon: ShieldCheck, description: "Data trust score, duplicate check, missing values audit, and data structure validation." },
  { title: "Dataset Explorer", category: "Data Inspection", url: "/explorer", icon: Database, description: "Inspect uploaded table layouts, columns, and sample records." },
  { title: "Executive Business Profile", category: "Briefing", url: "/profile", icon: Building2, description: "Business briefing background, ready capabilities, and strategy questions." },
  { title: "Data Lineage", category: "Process", url: "/lineage", icon: GitBranch, description: "End-to-end data flow visualization from raw upload to semantic model." },
  { title: "System Architecture", category: "Architecture", url: "/architecture", icon: Bot, description: "Interactive explorer of AI System, Forecast System, and Analytics Platform." }
];

export default function ExecutiveSearchModal({ open: controlledOpen, onClose: controlledOnClose }: ExecutiveSearchModalProps) {
  const router = useRouter();
  const [internalOpen, setInternalOpen] = useState(false);
  const [query, setQuery] = useState("");

  const isControlled = controlledOpen !== undefined;
  const isOpen = isControlled ? controlledOpen : internalOpen;

  const handleClose = useCallback(() => {
    if (isControlled && controlledOnClose) {
      controlledOnClose();
    } else {
      setInternalOpen(false);
    }
  }, [isControlled, controlledOnClose]);

  const handleOpen = useCallback(() => {
    if (!isControlled) {
      setInternalOpen(true);
    }
  }, [isControlled]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        handleOpen();
      }
      if (e.key === "Escape" && isOpen) {
        handleClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleOpen, handleClose]);

  const results = SEARCH_REGISTRY.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.category.toLowerCase().includes(query.toLowerCase()) ||
      item.description.toLowerCase().includes(query.toLowerCase())
  );

  function handleSelect(url: string) {
    handleClose();
    router.push(url);
  }

  return (
    <>
      {/* Search Bar Button in Navigation */}
      <button
        onClick={handleOpen}
        className="hidden md:flex items-center gap-2 px-4 py-2 bg-surface-muted hover:bg-border-color/80 text-text-secondary text-xs font-semibold rounded-xl transition-all border border-border-color"
        aria-label="Open search"
      >
        <Search className="w-3.5 h-3.5 text-text-muted" />
        <span>Search business (e.g. Profit, Shipping)...</span>
        <kbd className="ml-2 px-1.5 py-0.5 bg-surface text-[10px] font-mono text-text-muted rounded border border-border-color">
          ⌘K
        </kbd>
      </button>

      {/* Global Cmd+K Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-background/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div
            className="bg-surface rounded-2xl max-w-2xl w-full border border-border-color shadow-2xl overflow-hidden space-y-0 animate-scale-in"
            role="dialog"
            aria-modal="true"
            aria-label="Global search"
          >
            {/* Search Input Box */}
            <div className="p-4 border-b border-border-light flex items-center gap-3">
              <Search className="w-5 h-5 text-primary-600" aria-hidden="true" />
              <input
                type="text"
                autoFocus
                placeholder="Type anything (e.g. Profit, Revenue, Customers, Shipping, Forecast)..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 text-sm text-text-primary placeholder:text-text-muted outline-none bg-transparent font-medium"
                aria-label="Search"
              />
              <button
                onClick={handleClose}
                className="p-1 text-text-muted hover:text-text-secondary rounded-lg transition-colors"
                aria-label="Close search"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Search Results List */}
            <div className="max-h-96 overflow-y-auto p-3 space-y-1.5">
              {results.length === 0 ? (
                <div className="p-8 text-center text-xs text-text-muted">
                  No matching business results found for &quot;{query}&quot;.
                </div>
              ) : (
                results.map((res, idx) => {
                  const Icon = res.icon;
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleSelect(res.url)}
                      className="p-3.5 rounded-2xl hover:bg-primary-50/70 cursor-pointer transition-all flex items-center justify-between group border border-transparent hover:border-primary-100 w-full text-left"
                    >
                      <div className="flex items-center gap-3">
                          <div className="p-2 bg-primary-100 text-primary-700 rounded-xl group-hover:bg-primary-600 group-hover:text-white transition-colors">
                          <Icon className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-xs font-extrabold text-text-primary group-hover:text-primary-600 transition-colors">
                              {res.title}
                            </h4>
                            <span className="px-2 py-0.5 bg-surface-muted text-text-secondary text-[10px] font-mono font-bold rounded">
                              {res.category}
                            </span>
                          </div>
                          <p className="text-[11px] text-text-muted mt-0.5">{res.description}</p>
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-primary-600 transition-transform group-hover:translate-x-1" />
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
