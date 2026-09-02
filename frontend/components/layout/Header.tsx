"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Search,
  Bell,
  ChevronDown,
  Building2,
  HelpCircle,
  Menu,
  Moon,
  Sun,
  Command,
  CheckCircle2,
  CheckCheck,
  Info,
  AlertTriangle,
  X,
} from "lucide-react";
import ExecutiveSearchModal from "../dashboard/ExecutiveSearchModal";
import api, { invalidateCache } from "@/lib/api";
import { useTheme } from "@/components/theme/ThemeProvider";

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  time: string;
  unread: boolean;
  type: "info" | "success" | "warning";
}

const DEFAULT_NOTIFICATIONS: NotificationItem[] = [
  {
    id: "notif-1",
    title: "Universal Analytics Synced",
    message: "Active dataset fully verified and calibrated across 12 statistical engines.",
    time: "10m ago",
    unread: true,
    type: "success",
  },
  {
    id: "notif-2",
    title: "Enterprise Security Policy",
    message: "Strict CSP, HSTS, and JWT constant-time signature verification active.",
    time: "1h ago",
    unread: true,
    type: "info",
  },
  {
    id: "notif-3",
    title: "Scenario Lever Matrix Ready",
    message: "Driver decomposition models converged with high confidence.",
    time: "2h ago",
    unread: false,
    type: "info",
  },
];

interface UserProfile {
  full_name: string;
  email: string;
  role: string;
  organization?: string;
}

interface HeaderProps {
  onMobileMenuToggle?: () => void;
}

interface WorkspaceItem {
  workspace_id: string;
  name: string;
  industry?: string;
  is_active?: boolean;
}

export default function Header({ onMobileMenuToggle }: HeaderProps) {
  const pathname = usePathname();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [activeWorkspace, setActiveWorkspace] = useState("");
  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([]);
  const [wsLoading, setWsLoading] = useState(true);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>(DEFAULT_NOTIFICATIONS);

  const unreadCount = notifications.filter((n) => n.unread).length;

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, unread: false })));
  };

  const clearNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  useEffect(() => {
    if (!notifOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setNotifOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [notifOpen]);

  useEffect(() => {
    const stored = localStorage.getItem("decisionlens_user");
    let storedUser: UserProfile | null = null;
    if (stored) {
      try {
        storedUser = JSON.parse(stored);
      } catch (e) {
        console.warn("[Header] Failed to parse stored user", e);
      }
    }

    const token = typeof window !== "undefined" ? localStorage.getItem("decisionlens_access_token") : null;
    if (token) {
      api.get("/auth/me")
        .then((res) => {
          if (res.data) {
            setUser(res.data);
            if (typeof window !== "undefined") {
              localStorage.setItem("decisionlens_user", JSON.stringify(res.data));
            }
          } else if (storedUser) {
            setUser(storedUser);
          }
        })
        .catch((err) => {
          console.warn("[Header] Failed to load user profile", err);
          if (storedUser) {
            setUser(storedUser);
          }
        });
    } else if (storedUser) {
      setUser(storedUser);
    }

    api.get("/workspaces")
      .then((res) => {
        const data = res.data;
        if (data.workspaces) {
          setWorkspaces(data.workspaces);
          const storedActive = typeof window !== "undefined" ? localStorage.getItem("decisionlens_active_workspace") : null;
          const activeId = storedActive && data.workspaces.some((w: WorkspaceItem) => w.workspace_id === storedActive)
            ? storedActive
            : data.active_workspace_id || (data.workspaces.find((w: WorkspaceItem) => w.is_active)?.workspace_id || "");
          if (activeId) {
            setActiveWorkspace(activeId);
            if (typeof window !== "undefined") {
              localStorage.setItem("decisionlens_active_workspace", activeId);
            }
          }
        }
      })
      .catch((err) => {
        console.warn("[Header] Failed to load workspaces", err);
        setWorkspaces([]);
      })
      .finally(() => {
        setWsLoading(false);
      });
  }, []);

  async function handleWorkspaceChange(wsId: string) {
    setActiveWorkspace(wsId);
    if (typeof window !== "undefined") {
      localStorage.setItem("decisionlens_active_workspace", wsId);
      window.dispatchEvent(new CustomEvent("decisionlens:workspace_changed", { detail: { workspace_id: wsId } }));
    }
    invalidateCache();
    await api.post(`/workspaces/${wsId}/activate`).catch((err) => {
      console.warn("[Header] Failed to activate workspace", err);
    });
    window.location.reload();
  }

  function toggleTheme() {
    if (theme === "system") {
      setTheme(resolvedTheme === "light" ? "dark" : "light");
    } else {
      setTheme(theme === "light" ? "dark" : "light");
    }
  }

  const fullName = user?.full_name || "Enterprise User";
  const displayRole = user?.role || "User";
  const initials = fullName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2) || "EU";

  const segments = pathname.split("/").filter(Boolean);
  const breadcrumbs = segments.length === 0
    ? [{ label: "Dashboard", href: "/dynamic-dashboard", isLast: true }]
    : segments.map((segment, idx, arr) => ({
        label: segment === "dynamic-dashboard"
          ? "Dashboard"
          : segment.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        href: "/" + arr.slice(0, idx + 1).join("/"),
        isLast: idx === arr.length - 1,
      }));

  return (
    <header className="h-16 sticky top-0 z-30 flex items-center justify-between px-4 lg:px-6 bg-surface border-b border-border-color shadow-sm select-none" role="banner" aria-label="Site header">
      {/* Mobile menu toggle */}
      <div className="flex items-center gap-3 lg:hidden">
        <button
          onClick={onMobileMenuToggle}
          className="p-2 hover:bg-surface-muted rounded-lg text-text-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          aria-label="Toggle navigation menu"
          aria-expanded={false}
        >
          <Menu className="w-5 h-5" />
        </button>
        <span className="text-sm font-bold text-text-primary">DecisionLens</span>
      </div>

      {/* Desktop left section */}
      <div className="hidden lg:flex items-center gap-4 flex-1 min-w-0">
        <div className="flex items-center gap-2 shrink-0">
          <Building2 className="w-4 h-4 text-text-muted shrink-0" aria-hidden="true" />
          {wsLoading ? (
            <span className="text-xs font-semibold text-text-muted" role="status" aria-live="polite">Loading...</span>
          ) : (
            <div className="relative">
              <select
                value={activeWorkspace}
                onChange={(e) => handleWorkspaceChange(e.target.value)}
                className="text-xs font-semibold text-text-primary bg-surface-muted hover:bg-border-color/80 pl-3 pr-8 py-1.5 rounded-lg border border-border-color cursor-pointer outline-none transition-all focus-visible:ring-2 focus-visible:ring-primary-500 appearance-none"
                aria-label="Select active workspace"
              >
                {workspaces.length > 0 ? (
                  workspaces.map((ws) => (
                    <option key={ws.workspace_id} value={ws.workspace_id}>
                      {ws.name} ({ws.industry || "Enterprise"})
                    </option>
                  ))
                ) : (
                  <option value="">Active Workspace</option>
                )}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-text-muted absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" aria-hidden="true" />
            </div>
          )}
        </div>

        {/* Breadcrumbs */}
        <nav className="hidden md:flex items-center gap-1.5 text-xs text-text-muted font-medium min-w-0" aria-label="Breadcrumb">
          {breadcrumbs.map((crumb, idx) => (
            <React.Fragment key={crumb.href}>
              {idx > 0 && (
                <span className="text-border-strong mx-0.5 select-none" aria-hidden="true">/</span>
              )}
              {crumb.isLast ? (
                <span
                  className="text-text-primary font-semibold truncate max-w-[200px]"
                  aria-current="page"
                >
                  {crumb.label}
                </span>
              ) : (
                <Link
                  href={crumb.href}
                  className="hover:text-text-primary transition-colors hover:underline underline-offset-4 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 rounded px-1 -mx-1"
                >
                  {crumb.label}
                </Link>
              )}
            </React.Fragment>
          ))}
        </nav>
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-1.5">
        {/* Global Search Trigger */}
        <button
          onClick={() => setSearchOpen(true)}
          className="hidden sm:flex items-center gap-2 h-9 px-3 rounded-lg border border-border-color bg-surface-muted text-text-muted hover:bg-surface-muted hover:text-text-secondary transition-all text-xs cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          aria-label="Open global search (Press Cmd+K)"
        >
          <Search className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
          <span className="hidden md:inline">Search...</span>
          <kbd
            className="hidden md:inline-flex items-center gap-0.5 ml-2 px-1.5 py-0.5 rounded bg-surface border border-border-color text-[10px] font-mono text-text-muted shadow-sm"
            aria-hidden="true"
          >
            <Command className="w-2.5 h-2.5" aria-hidden="true" />
            K
          </kbd>
        </button>

        {/* Mobile search */}
        <button
          onClick={() => setSearchOpen(true)}
          className="sm:hidden h-9 w-9 rounded-lg border border-border-color bg-surface flex items-center justify-center text-text-secondary hover:bg-surface-muted transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          aria-label="Open global search"
        >
          <Search className="w-4 h-4" aria-hidden="true" />
        </button>

        <ExecutiveSearchModal open={searchOpen} onClose={() => setSearchOpen(false)} />

        {/* Notifications Dropdown */}
        <div className="relative">
          <button
            onClick={() => setNotifOpen(!notifOpen)}
            className="relative h-9 w-9 rounded-lg border border-border-color bg-surface flex items-center justify-center text-text-secondary hover:bg-surface-muted transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 active:scale-[0.97]"
            aria-label={`Notifications ${unreadCount > 0 ? `(${unreadCount} unread)` : ""}`}
            aria-expanded={notifOpen}
            aria-haspopup="dialog"
          >
            <Bell className="w-4 h-4" aria-hidden="true" />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-primary-600 ring-2 ring-surface animate-pulse" aria-hidden="true" />
            )}
          </button>

          {/* Notification Center Popover */}
          {notifOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setNotifOpen(false)} aria-hidden="true" />
              <div
                className="absolute right-0 top-full mt-2 w-80 sm:w-96 bg-surface rounded-2xl border border-border-color shadow-xl z-50 animate-scale-in overflow-hidden"
                role="region"
                aria-label="Notification center"
              >
                <div className="px-4 py-3 border-b border-border-light flex items-center justify-between bg-surface-muted/30">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-bold text-text-primary">Notifications</p>
                    {unreadCount > 0 && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-primary-50 text-primary-600 border border-primary-200">
                        {unreadCount} new
                      </span>
                    )}
                  </div>
                  {notifications.length > 0 && (
                    <button
                      type="button"
                      onClick={markAllAsRead}
                      className="text-[11px] font-semibold text-primary-600 hover:text-primary-700 transition-colors flex items-center gap-1 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary-500 rounded"
                    >
                      <CheckCheck className="w-3.5 h-3.5" aria-hidden="true" />
                      <span>Mark all read</span>
                    </button>
                  )}
                </div>

                <div className="max-h-80 overflow-y-auto divide-y divide-border-light">
                  {notifications.length === 0 ? (
                    <div className="p-6 text-center">
                      <CheckCircle2 className="w-8 h-8 text-success-500 mx-auto mb-2 opacity-80" aria-hidden="true" />
                      <p className="text-xs font-semibold text-text-primary">All caught up!</p>
                      <p className="text-[11px] text-text-muted mt-0.5">No notifications at this time.</p>
                    </div>
                  ) : (
                    notifications.map((notif) => (
                      <div
                        key={notif.id}
                        className={`p-3.5 flex items-start gap-3 transition-colors ${
                          notif.unread ? "bg-primary-50/20 hover:bg-primary-50/40" : "hover:bg-surface-muted/50"
                        }`}
                      >
                        <div className="mt-0.5 shrink-0">
                          {notif.type === "success" ? (
                            <CheckCircle2 className="w-4 h-4 text-success-600" aria-hidden="true" />
                          ) : notif.type === "warning" ? (
                            <AlertTriangle className="w-4 h-4 text-warning-600" aria-hidden="true" />
                          ) : (
                            <Info className="w-4 h-4 text-primary-600" aria-hidden="true" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <p className={`text-xs ${notif.unread ? "font-bold text-text-primary" : "font-medium text-text-secondary"}`}>
                              {notif.title}
                            </p>
                            <span className="text-[10px] text-text-muted shrink-0">{notif.time}</span>
                          </div>
                          <p className="text-[11px] text-text-muted mt-0.5 line-clamp-2 leading-relaxed">
                            {notif.message}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => clearNotification(notif.id)}
                          className="text-text-muted hover:text-text-primary p-1 rounded transition-colors -mr-1 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary-500"
                          aria-label={`Dismiss notification: ${notif.title}`}
                        >
                          <X className="w-3 h-3" aria-hidden="true" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="h-9 w-9 rounded-lg border border-border-color bg-surface flex items-center justify-center text-text-secondary hover:bg-surface-muted transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 active:scale-[0.97] hidden sm:flex"
          aria-label={`Switch to ${resolvedTheme === "light" ? "dark" : "light"} mode`}
          title={`Switch to ${resolvedTheme === "light" ? "dark" : "light"} mode`}
        >
          {resolvedTheme === "light" ? (
            <Moon className="w-4 h-4" aria-hidden="true" />
          ) : (
            <Sun className="w-4 h-4" aria-hidden="true" />
          )}
        </button>

        <Link
          href="/help"
          className="h-9 w-9 rounded-lg border border-border-color bg-surface flex items-center justify-center text-text-secondary hover:bg-surface-muted transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 active:scale-[0.97] hidden md:flex"
          title="Help & Documentation"
          aria-label="Help & Documentation"
        >
          <HelpCircle className="w-4 h-4" aria-hidden="true" />
        </Link>

        <Link
          href="/profile"
          className="flex items-center gap-2 pl-2.5 border-l border-border-color hover:opacity-80 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 rounded-lg"
          aria-label="User profile and settings"
        >
          <div className="h-8 w-8 rounded-full bg-primary-600 text-white font-bold text-xs flex items-center justify-center shadow-sm">
            {initials}
          </div>
          <div className="hidden lg:block text-left">
            <p className="text-xs font-semibold text-text-primary leading-tight">{fullName}</p>
            <p className="text-[10px] text-primary-600 dark:text-primary-400 font-medium capitalize">{displayRole.replace("_", " ").toLowerCase()}</p>
          </div>
        </Link>
      </div>
    </header>
  );
}
