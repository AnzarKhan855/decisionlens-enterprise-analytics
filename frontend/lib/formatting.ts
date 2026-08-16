import type { MetricObject } from "./types";

export function formatBusinessValue(metricName: string, value: number | string | MetricObject | null | undefined | unknown, currencySymbol: string = "$"): string {
  if (value === null || value === undefined) return "No data";

  let valNum: number;
  if (typeof value === "number") {
    valNum = value;
  } else if (typeof value === "string") {
    return value;
  } else if (Array.isArray(value)) {
    return "No data";
  } else if (typeof value === "object") {
    const m = value as Record<string, unknown>;
    if (typeof m.formatted_value === "string") return m.formatted_value;
    if (typeof m.value === "number") valNum = m.value;
    else if (typeof m.value === "string") {
      const cleaned = m.value.replace(/[^0-9.-]/g, "");
      const parsed = parseFloat(cleaned);
      return isNaN(parsed) ? String(m.value) : String(parsed);
    } else {
      return "N/A";
    }
  } else {
    return "No data";
  }

  // Normalize negative zero or tiny floating point numbers
  if (Object.is(valNum, -0) || Math.abs(valNum) < 1e-9) {
    valNum = 0;
  }

  const nameClean = (metricName || "").toLowerCase().replace(/_/g, " ");

  const nonCurrencyKeywords = ["id", "uuid", "code", "age", "qty", "quantity", "count", "rating", "score", "rows", "columns", "units", "year", "month", "rank"];
  const percentageKeywords = ["rate", "percentage", "margin", "growth", "retention", "share", "ratio", "roi", "churn", "accuracy", "confidence"];
  const currencyKeywords = ["revenue", "sales", "profit", "cost", "price", "discount", "amount", "expense", "income", "salary", "balance", "fee", "tax", "budget"];

  if (nonCurrencyKeywords.some((kw) => nameClean.split(" ").includes(kw) || nameClean.endsWith(kw))) {
    return Number.isInteger(valNum) ? valNum.toLocaleString() : valNum.toFixed(2);
  }

  if (percentageKeywords.some((kw) => nameClean.includes(kw))) {
    const pct = Math.abs(valNum) <= 1 ? valNum * 100 : valNum;
    return `${pct.toFixed(1)}%`;
  }

  if (currencyKeywords.some((kw) => nameClean.includes(kw))) {
    if (Math.abs(valNum) >= 1_000_000_000) return `${currencySymbol}${(valNum / 1_000_000_000).toFixed(2)}B`;
    if (Math.abs(valNum) >= 1_000_000) return `${currencySymbol}${(valNum / 1_000_000).toFixed(2)}M`;
    if (Math.abs(valNum) >= 1_000) return `${currencySymbol}${valNum.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    return `${currencySymbol}${valNum.toFixed(2)}`;
  }

  return Number.isInteger(valNum) ? valNum.toLocaleString() : valNum.toFixed(2);
}

export function normalizeConfidence(value: unknown): number {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return 0;
    if (value >= 0 && value <= 1) {
      return Math.round(value * 100);
    }
    return Math.round(Math.max(0, Math.min(100, value)));
  }
  if (typeof value === "string") {
    const cleaned = value.replace(/%/g, "").trim();
    const num = parseFloat(cleaned);
    if (isNaN(num) || !Number.isFinite(num)) return 0;
    if (num >= 0 && num <= 1) {
      return Math.round(num * 100);
    }
    return Math.round(Math.max(0, Math.min(100, num)));
  }
  return 0;
}
