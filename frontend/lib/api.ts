import axios, { type AxiosResponse, type AxiosRequestConfig } from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
export { API_BASE_URL };

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

const _requestCache = new Map<string, CacheEntry<unknown>>();
const _inFlightRequests = new Map<string, Promise<unknown>>();
const _cacheTTL = 30000;

function cacheKey(url: string, params?: Record<string, unknown>): string {
  const paramStr = params ? JSON.stringify(params) : "";
  return `${url}:${paramStr}`;
}

function getFromCache<T>(key: string): T | null {
  const entry = _requestCache.get(key) as CacheEntry<T> | undefined;
  if (!entry) return null;
  if (Date.now() - entry.timestamp > entry.ttl) {
    _requestCache.delete(key);
    return null;
  }
  return entry.data;
}

function setCache<T>(key: string, data: T, ttl: number = _cacheTTL): void {
  _requestCache.set(key, { data, timestamp: Date.now(), ttl });
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      let token = localStorage.getItem("decisionlens_access_token") || localStorage.getItem("token");
      if (!token && typeof document !== "undefined") {
        const match = document.cookie.match(/(?:^|;\s*)decisionlens_token=([^;]+)/);
        if (match) token = decodeURIComponent(match[1]);
      }
      if (token && config.headers) {
        if (typeof config.headers.set === "function") {
          config.headers.set("Authorization", `Bearer ${token.trim()}`);
        } else {
          config.headers["Authorization"] = `Bearer ${token.trim()}`;
        }
      }
      const activeWs = localStorage.getItem("decisionlens_active_workspace");
      if (activeWs && config.headers) {
        if (typeof config.headers.set === "function") {
          if (!config.headers.get("X-Workspace-Id")) {
            config.headers.set("X-Workspace-Id", activeWs.trim());
          }
        } else if (!config.headers["X-Workspace-Id"]) {
          config.headers["X-Workspace-Id"] = activeWs.trim();
        }
      }
    }
    if (config.data instanceof FormData && config.headers) {
      if (typeof config.headers.delete === "function") {
        config.headers.delete("Content-Type");
        config.headers.delete("content-type");
      } else {
        delete config.headers["Content-Type"];
        delete config.headers["content-type"];
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export type ErrorCategory =
  | "TIMEOUT"
  | "NETWORK_ERROR"
  | "AUTH_ERROR"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "DATASET_PROCESSING"
  | "SERVER_ERROR"
  | "CLIENT_ERROR"
  | "UNKNOWN_ERROR";

api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail || error.response?.data?.message || "";
    const detailLower = typeof detail === "string" ? detail.toLowerCase() : "";

    if (error.code === "ECONNABORTED" || (error.message && error.message.toLowerCase().includes("timeout"))) {
      error.errorCategory = "TIMEOUT" as ErrorCategory;
      error.userFriendlyMessage = "The request timed out while waiting for the server to process data.";
      error.message = "The request timed out. Please check your network connection and try again.";
    } else if (!error.response) {
      error.errorCategory = "NETWORK_ERROR" as ErrorCategory;
      error.userFriendlyMessage = "Unable to connect to the DecisionLens API. Please verify network connectivity.";
      error.message = "Unable to connect to the server. Please ensure the backend is running.";
    } else if (status === 401) {
      error.errorCategory = "AUTH_ERROR" as ErrorCategory;
      const reqUrl = error.config?.url || "";
      const isAuthEndpoint = reqUrl.includes("/auth/login") || reqUrl.includes("/auth/register") || reqUrl.includes("/auth/forgot-password") || reqUrl.includes("/auth/reset-password") || reqUrl.includes("/auth/verify-otp");

      if (typeof window !== "undefined" && !isAuthEndpoint) {
        localStorage.removeItem("decisionlens_access_token");
        localStorage.removeItem("decisionlens_refresh_token");
        localStorage.removeItem("decisionlens_user");
        document.cookie = "decisionlens_token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT; SameSite=Lax;";
      }
      if (typeof window !== "undefined" && !isAuthEndpoint && !window.location.pathname.startsWith("/login")) {
        const fullPath = window.location.pathname + window.location.search;
        const redirectParam = fullPath && fullPath !== "/" ? `?redirect=${encodeURIComponent(fullPath)}` : "";
        window.location.href = `/login${redirectParam}`;
      }

      if (isAuthEndpoint) {
        error.message = error.response?.data?.detail || error.response?.data?.message || "Invalid credentials or authentication request failed.";
      } else {
        error.message = "Session expired. Please sign in again.";
      }
      error.userFriendlyMessage = error.message;
    } else if (status === 403) {
      error.errorCategory = "FORBIDDEN" as ErrorCategory;
      error.userFriendlyMessage = typeof detail === "string" && detail ? detail : "Access Denied: You do not have permission for this action.";
      error.message = error.userFriendlyMessage;
    } else if (status === 404) {
      error.errorCategory = "NOT_FOUND" as ErrorCategory;
      error.userFriendlyMessage = "The requested resource or workspace was not found.";
      error.message = error.userFriendlyMessage;
    } else if (status === 422 || (status === 400 && (detailLower.includes("processing") || detailLower.includes("dataset") || detailLower.includes("ingestion")))) {
      error.errorCategory = "DATASET_PROCESSING" as ErrorCategory;
      error.userFriendlyMessage = typeof detail === "string" && detail ? detail : "Dataset processing error. Please verify file format and columns.";
      error.message = error.userFriendlyMessage;
    } else if (status && status >= 500) {
      error.errorCategory = "SERVER_ERROR" as ErrorCategory;
      error.userFriendlyMessage = "An internal server error occurred. Please try again later.";
      error.message = error.userFriendlyMessage;
    } else {
      error.errorCategory = "CLIENT_ERROR" as ErrorCategory;
      error.userFriendlyMessage = typeof detail === "string" && detail ? detail : "Request failed.";
    }

    if (error.response?.data && !error.response.data.detail && error.response.data.reason) {
      error.response.data = {
        ...error.response.data,
        detail: error.response.data.reason,
      };
    }

    return Promise.reject(error);
  }
);

export async function getCached<T>(url: string, params?: Record<string, unknown>, ttl?: number): Promise<T> {
  const key = cacheKey(url, params);
  const cached = getFromCache<T>(key);
  if (cached !== null) {
    return cached;
  }

  const inFlight = _inFlightRequests.get(key);
  if (inFlight) {
    return inFlight as Promise<T>;
  }

  const promise = api.get<T>(url, { params })
    .then((response) => {
      setCache(key, response.data, ttl);
      return response.data;
    })
    .finally(() => {
      _inFlightRequests.delete(key);
    });

  _inFlightRequests.set(key, promise);
  return promise;
}

export async function postCached<T>(url: string, data?: unknown, ttl?: number): Promise<T> {
  const isMutation = url.includes("/simulate") || url.includes("/generate") || url.includes("/submit") || url.includes("/copilot") || url.includes("/ai/");
  if (isMutation) {
    return api.post<T>(url, data).then((response) => response.data);
  }

  const key = cacheKey(url, data as Record<string, unknown>);
  const cached = getFromCache<T>(key);
  if (cached !== null) {
    return cached;
  }

  const inFlight = _inFlightRequests.get(key);
  if (inFlight) {
    return inFlight as Promise<T>;
  }

  const promise = api.post<T>(url, data)
    .then((response) => {
      setCache(key, response.data, ttl);
      return response.data;
    })
    .finally(() => {
      _inFlightRequests.delete(key);
    });

  _inFlightRequests.set(key, promise);
  return promise;
}

export function invalidateCache(url?: string): void {
  if (url) {
    for (const key of _requestCache.keys()) {
      if (key.startsWith(url)) {
        _requestCache.delete(key);
      }
    }
  } else {
    _requestCache.clear();
  }
}

export const apiGet = <T>(url: string, params?: Record<string, unknown>): Promise<T> =>
  getCached<T>(url, params);

export const apiPost = <T>(url: string, data?: unknown): Promise<T> =>
  postCached<T>(url, data);

export const apiPostDirect = <T>(url: string, data?: unknown, config?: Record<string, unknown>): Promise<T> =>
  api.post<T>(url, data, config).then((res) => res.data);

export const apiGetDirect = <T>(url: string, params?: Record<string, unknown>, config?: Record<string, unknown>): Promise<T> =>
  api.get<T>(url, { params, ...config }).then((res) => res.data);

// Transparent GET deduplication & short-window caching
const _nativeGet = api.get.bind(api);
const _nativePost = api.post.bind(api);
const _nativePut = api.put.bind(api);
const _nativePatch = api.patch.bind(api);
const _nativeDelete = api.delete.bind(api);

api.get = function <T = any, R = AxiosResponse<T>, D = any>(
  url: string,
  config?: AxiosRequestConfig<D>
): Promise<R> {
  if (typeof window === "undefined" || config?.responseType === "blob" || (config as any)?.skipCache) {
    return _nativeGet(url, config);
  }

  const key = cacheKey(url, config?.params as Record<string, unknown>);

  const inFlight = _inFlightRequests.get(key);
  if (inFlight) {
    return inFlight as Promise<R>;
  }

  const cached = getFromCache<R>(key);
  if (cached !== null) {
    return Promise.resolve(cached);
  }

  const promise = _nativeGet<T, R, D>(url, config)
    .then((response) => {
      // Cache for 5 seconds to deduplicate burst loads from layout + page
      setCache(key, response, 5000);
      return response;
    })
    .finally(() => {
      _inFlightRequests.delete(key);
    });

  _inFlightRequests.set(key, promise as Promise<unknown>);
  return promise;
} as typeof api.get;

// Auto-invalidate cache on data mutations
api.post = function <T = any, R = AxiosResponse<T>, D = any>(
  url: string,
  data?: D,
  config?: AxiosRequestConfig<D>
): Promise<R> {
  invalidateCache();
  return _nativePost(url, data, config);
} as typeof api.post;

api.put = function <T = any, R = AxiosResponse<T>, D = any>(
  url: string,
  data?: D,
  config?: AxiosRequestConfig<D>
): Promise<R> {
  invalidateCache();
  return _nativePut(url, data, config);
} as typeof api.put;

api.patch = function <T = any, R = AxiosResponse<T>, D = any>(
  url: string,
  data?: D,
  config?: AxiosRequestConfig<D>
): Promise<R> {
  invalidateCache();
  return _nativePatch(url, data, config);
} as typeof api.patch;

api.delete = function <T = any, R = AxiosResponse<T>, D = any>(
  url: string,
  config?: AxiosRequestConfig<D>
): Promise<R> {
  invalidateCache();
  return _nativeDelete(url, config);
} as typeof api.delete;

export default api;