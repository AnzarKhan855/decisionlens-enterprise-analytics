import axios from "axios";

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
      const token = localStorage.getItem("decisionlens_access_token") || localStorage.getItem("token");
      if (token && config.headers) {
        if (typeof config.headers.set === "function") {
          config.headers.set("Authorization", `Bearer ${token.trim()}`);
        } else {
          config.headers["Authorization"] = `Bearer ${token.trim()}`;
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

api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.code === "ECONNABORTED") {
      error.message = "The request timed out. Please check your network connection and try again.";
    } else if (!error.response) {
      error.message = "Unable to connect to the server. Please ensure the backend is running.";
    } else if (error.response.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("decisionlens_access_token");
        localStorage.removeItem("decisionlens_refresh_token");
        localStorage.removeItem("decisionlens_user");
      }
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
      error.message = "Session expired. Please sign in again.";
    } else if (error.response.status === 404) {
      error.message = "The requested resource was not found.";
    } else if (error.response.status === 500) {
      error.message = "An internal server error occurred. Please try again later.";
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

  const promise = api.get<T>(url, { params }).then((response) => {
    setCache(key, response.data, ttl);
    _inFlightRequests.delete(key);
    return response.data;
  }).catch((err) => {
    _inFlightRequests.delete(key);
    throw err;
  });

  _inFlightRequests.set(key, promise);
  return promise;
}

export async function postCached<T>(url: string, data?: unknown, ttl?: number): Promise<T> {
  if (typeof data === "object" && data !== null) {
    const d = data as Record<string, unknown>;
    if (d.question !== undefined || url.includes("/copilot/query") || url.includes("/ai/copilot/query") || url.includes("/ai/query")) {
      return api.post<T>(url, data).then((response) => response.data);
    }
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

  const promise = api.post<T>(url, data).then((response) => {
    setCache(key, response.data, ttl);
    _inFlightRequests.delete(key);
    return response.data;
  }).catch((err) => {
    _inFlightRequests.delete(key);
    throw err;
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

export default api;