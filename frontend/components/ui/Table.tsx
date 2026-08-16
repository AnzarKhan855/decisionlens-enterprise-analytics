"use client";

import React, { useState, useMemo } from "react";
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight } from "lucide-react";

interface Column<T> {
  key: string;
  header: string;
  width?: string;
  align?: "left" | "center" | "right";
  sortable?: boolean;
  render?: (row: T, index: number) => React.ReactNode;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  emptyState?: React.ReactNode;
  loading?: boolean;
  rowKey?: (row: T, index: number) => string | number;
  onRowClick?: (row: T, index: number) => void;
  className?: string;
  caption?: string;
  stickyHeader?: boolean;
  zebra?: boolean;
  hoverable?: boolean;
  compact?: boolean;
  sortable?: boolean;
  pageSize?: number;
}

const defaultSkeletonRows = Array.from({ length: 5 }).map((_, i) => i);

export default function Table<T>({
  columns,
  data,
  emptyState,
  loading = false,
  rowKey = (_row: T, index: number) => index,
  onRowClick,
  className = "",
  caption,
  stickyHeader = true,
  zebra = true,
  hoverable = true,
  compact = false,
  sortable = false,
  pageSize = 10,
}: TableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [currentPage, setCurrentPage] = useState(1);

  const sortedData = useMemo(() => {
    if (!sortKey || !sortable) return data;
    return [...data].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sortKey];
      const bVal = (b as Record<string, unknown>)[sortKey];
      if (aVal === bVal) return 0;
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      const cmp = aVal < bVal ? -1 : 1;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir, sortable]);

  const totalPages = Math.max(1, Math.ceil(sortedData.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const paginatedData = useMemo(() => {
    const start = (safePage - 1) * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [sortedData, safePage, pageSize]);

  const handleSort = (col: Column<T>) => {
    if (!col.sortable && !sortable) return;
    const key = col.key;
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const getSortIcon = (col: Column<T>) => {
    if (!sortable && !col.sortable) return null;
    if (sortKey !== col.key) {
      return <ChevronsUpDown className="w-3.5 h-3.5 text-text-muted/60" aria-hidden="true" />;
    }
    return sortDir === "asc" ? (
      <ChevronUp className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
    ) : (
      <ChevronDown className="w-3.5 h-3.5 text-primary-600" aria-hidden="true" />
    );
  };

  const alignClass = (align?: string) => {
    if (align === "center") return "text-center";
    if (align === "right") return "text-right";
    return "text-left";
  };

  const renderBody = () => {
    if (loading) {
      return (
        <tbody>
          {defaultSkeletonRows.map((rowIndex) => (
            <tr key={`skeleton-${rowIndex}`} className={compact ? "h-10" : "h-14"}>
              {columns.map((col, colIndex) => (
                <td key={`skeleton-${colIndex}`}>
                  <div
                    className="skeleton-shimmer rounded-md"
                    style={{
                      height: compact ? "0.75rem" : "1rem",
                      width: colIndex === 0 ? "70%" : "50%",
                      margin: "0.25rem 0",
                    }}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      );
    }

    if (sortedData.length === 0 && emptyState) {
      return (
        <tbody>
          <tr>
            <td colSpan={columns.length} className="text-center py-16">
              {emptyState}
            </td>
          </tr>
        </tbody>
      );
    }

    if (sortedData.length === 0) {
      return (
        <tbody>
          <tr>
            <td colSpan={columns.length} className="text-center py-16 text-text-muted text-sm">
              No data available
            </td>
          </tr>
        </tbody>
      );
    }

    return (
      <tbody>
        {paginatedData.map((row, index) => {
          const actualIndex = (safePage - 1) * pageSize + index;
          const isZebra = zebra && actualIndex % 2 === 1;
          return (
            <tr
              key={rowKey(row, actualIndex)}
              className={`
                transition-colors duration-150
                ${onRowClick || hoverable ? "cursor-pointer" : ""}
                ${hoverable ? "hover:bg-surface-muted/60" : ""}
                ${isZebra ? "bg-surface-muted/30" : ""}
                ${onRowClick ? "hover:bg-primary-50/40 dark:hover:bg-primary-900/20" : ""}
              `}
              onClick={onRowClick ? () => onRowClick(row, actualIndex) : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              onKeyDown={
                onRowClick
                  ? (e: React.KeyboardEvent<HTMLTableRowElement>) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onRowClick(row, actualIndex);
                      }
                    }
                  : undefined
              }
              role={onRowClick ? "button" : undefined}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`
                    ${alignClass(col.align)}
                    ${compact ? "py-2.5 px-4 text-xs" : "py-3.5 px-5 text-sm"}
                  `}
                >
                  {col.render ? col.render(row, actualIndex) : (row as Record<string, unknown>)[col.key]?.toString() ?? ""}
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    );
  };

  const renderPagination = () => {
    if (totalPages <= 1) return null;
    return (
      <div className="flex items-center justify-between px-5 py-3.5 border-t border-border-color">
        <div className="text-xs text-text-muted">
          Showing {(safePage - 1) * pageSize + 1} to {Math.min(safePage * pageSize, sortedData.length)} of {sortedData.length} entries
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={safePage === 1}
            className="p-1.5 rounded-lg border border-border-color bg-surface hover:bg-surface-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            aria-label="Previous page"
          >
            <ChevronLeft className="w-4 h-4 text-text-secondary" aria-hidden="true" />
          </button>
          {Array.from({ length: Math.min(totalPages, 7) }).map((_, i) => {
            let pageNum: number;
            if (totalPages <= 7) {
              pageNum = i + 1;
            } else if (safePage <= 4) {
              pageNum = i + 1;
            } else if (safePage >= totalPages - 3) {
              pageNum = totalPages - 6 + i;
            } else {
              pageNum = safePage - 3 + i;
            }
            const isActive = pageNum === safePage;
            return (
              <button
                key={pageNum}
                type="button"
                onClick={() => setCurrentPage(pageNum)}
                className={`
                  min-w-[2rem] h-8 px-2 rounded-lg text-xs font-semibold transition-all
                  ${isActive ? "bg-primary-600 text-white shadow-sm" : "bg-surface border border-border-color text-text-secondary hover:bg-surface-muted"}
                `}
                aria-current={isActive ? "page" : undefined}
                aria-label={`Page ${pageNum}`}
              >
                {pageNum}
              </button>
            );
          })}
          <button
            type="button"
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={safePage === totalPages}
            className="p-1.5 rounded-lg border border-border-color bg-surface hover:bg-surface-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            aria-label="Next page"
          >
            <ChevronRight className="w-4 h-4 text-text-secondary" aria-hidden="true" />
          </button>
        </div>
      </div>
    );
  };

  const headerCellClass = compact
    ? "py-2.5 px-4 text-[11px]"
    : "py-3.5 px-5 text-xs";

  return (
    <div
      className={`
        table-container rounded-2xl border border-border-color bg-surface
        ${className}
      `}
      role="region"
      aria-label={caption || "Data table"}
      tabIndex={0}
    >
      <div className="overflow-x-auto -mx-5 sm:mx-0">
        <table aria-busy={loading} className="min-w-full">
          {caption && <caption className="sr-only">{caption}</caption>}
          <thead style={stickyHeader ? { position: "sticky", top: 0, zIndex: 10 } : undefined}>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  style={col.width ? { width: col.width } : undefined}
                  className={`
                    ${headerCellClass}
                    font-semibold uppercase tracking-wider text-text-secondary
                    border-b border-border-color whitespace-nowrap
                    ${(sortable || col.sortable) ? "cursor-pointer select-none hover:text-text-primary transition-colors" : ""}
                  `}
                  onClick={() => handleSort(col)}
                  aria-sort={
                    sortable || col.sortable
                      ? sortKey === col.key
                        ? sortDir === "asc"
                          ? "ascending"
                          : "descending"
                        : "none"
                      : undefined
                  }
                >
                  <span className="inline-flex items-center gap-1.5">
                    {col.header}
                    {getSortIcon(col)}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          {renderBody()}
        </table>
      </div>
      {renderPagination()}
    </div>
  );
}
