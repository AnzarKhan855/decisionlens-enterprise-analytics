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
} from "lucide-react";
import ExecutiveSearchModal from "../dashboard/ExecutiveSearchModal";
import api, { invalidateCache } from "@/lib/api";
import { useTheme } from "@/components/theme/ThemeProvider";

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
            : data.active_workspace_id || (data.workspaces.length > 0 ? data.workspaces[0].workspace_id : "");
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
    }
    invalidateCache();
    await api.post(`/workspaces/${wsId}/activate`).catch((err) => {
      console.warn("[Header] Failed to activate workspace", err);
    });
    window.location.href = "/dynamic-dashboard";
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

  const breadcrumbs = pathname
    .split("/")
    .filter(Boolean)
    .map((segment, idx, arr) => ({
      label: segment
        .replace(/-/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase()),
      href: "/" + (arr.slice(0, idx + 1).join("/")),
      isLast: idx === arr.length - 1,
    }));

  return (
    <header className="h-16 sticky top-0 z-30 flex items-center justify-between px-4 lg:px-6 bg-surface border-b border-border-color shadow-sm select-none" role="banner" aria-label="Site header">
      {/* Mobile menu toggle */}
      <div className="flex items-center gap-3 lg:hidden">
        <button
          onClick={onMobileMenuToggle}
          className="p-2 hover:bg-surface-muted rounded-lg text-text-secondary transition-colors"
          aria-label="Toggle navigation menu"
          aria-expanded={false}
        >
          <Menu className="w-5 h-5" />
        </button>
        <span className="text-sm font-bold text-text-primary">DecisionLens</span>
      </div>

      {/* Desktop left section */}
      <div className="hidden lg:flex items-center gap-4 flex-1">
        <div className="flex items-center gap-2">
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
        {breadcrumbs.length > 0 && (
          <nav className="hidden md:flex items-center gap-1 text-xs text-text-muted font-medium" aria-label="Breadcrumb">
            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={crumb.href}>
                {idx > 0 && (
                  <span className="text-text-muted mx-1" aria-hidden="true">/</span>
                )}
                <span
                  className={`
                    transition-colors
                    ${crumb.isLast
                      ? "text-text-primary font-semibold"
                      : "hover:text-text-secondary cursor-default"
                    }
                  `}
                  aria-current={crumb.isLast ? "page" : undefined}
                >
                  {crumb.label}
                </span>
              </React.Fragment>
            ))}
          </nav>
        )}
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-1.5">
        {/* Global Search Trigger */}
        <button
          onClick={() => setSearchOpen(true)}
          className="hidden sm:flex items-center gap-2 h-9 px-3 rounded-lg border border-border-color bg-surface-muted text-text-muted hover:bg-surface-muted hover:text-text-secondary transition-all text-xs cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500"
          aria-label="Open global search"
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
          className="sm:hidden h-9 w-9 rounded-lg border border-border-color bg-surface flex items-center justify-center text-text-secondary hover:bg-surface-muted transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500"
          aria-label="Open global search"
        >
          <Search className="w-4 h-4" aria-hidden="true" />
        </button>

        <ExecutiveSearchModal open={searchOpen} onClose={() => setSearchOpen(false)} />

        {/* Notifications Dropdown (placeholder) */}
        <div className="relative">
          <button
            onClick={() => setNotifOpen(!notifOpen)}
            className="relative h-9 w-9 rounded-lg border border-border-color bg-surface flex items-center justify-center text-text-secondary hover:bg-surface-muted transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 active:scale-[0.97]"
            aria-label="Notifications"
            aria-expanded={notifOpen}
            aria-haspopup="true"
          >
            <Bell className="w-4 h-4" aria-hidden="true" />
            <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-info-600 animate-pulse" aria-hidden="true" />
          </button>

          {/* Notification Dropdown Placeholder */}
          {notifOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setNotifOpen(false)} aria-hidden="true" />
              <div
                className="absolute right-0 top-full mt-2 w-80 bg-surface rounded-2xl border border-border-color shadow-lg z-50 animate-scale-in overflow-hidden"
                role="menu"
                aria-label="Notifications"
              >
                <div className="px-4 py-3 border-b border-border-light flex items-center justify-between">
                  <p className="text-sm font-bold text-text-primary">Notifications</p>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-primary-50 text-primary-600 border border-primary-200">
                    3 new
                  </span>
                </div>
                <div className="p-4 text-center">
                  <p className="text-xs text-text-muted">Notification dropdown placeholder</p>
                  <p className="text-[11px] text-text-muted mt-1">Connect to notifications API</p>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="h-9 w-9 rounded-lg border border-border-color bg-surface flex items-center justify-center text-text-secondary hover:bg-surface-muted transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-primary-500 active:scale-[0.97] hidden sm:flex"
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
          className="h-9 w-9 rounded-lg border border-border-color bg-surface flex items-center justify-center text-text-secondary hover:bg-surface-muted transition-all focus-visible:ring-2 focus-visible:ring-primary-500 active:scale-[0.97] hidden md:flex"
          title="Help & Documentation"
          aria-label="Help & Documentation"
        >
          <HelpCircle className="w-4 h-4" aria-hidden="true" />
        </Link>

        <Link
          href="/profile"
          className="flex items-center gap-2 pl-2.5 border-l border-border-color hover:opacity-80 transition-opacity"
          aria-label="User menu"
        >
           <div className="h-8 w-8 rounded-full bg-primary-600 text-text-primary font-bold text-xs flex items-center justify-center shadow-sm">
            {initials}
          </div>
          <div className="hidden lg:block text-left">
            <p className="text-xs font-semibold text-text-primary leading-tight">{fullName}</p>
            <p className="text-[10px] text-primary-600 font-medium capitalize">{displayRole.replace("_", " ").toLowerCase()}</p>
          </div>
        </Link>
      </div>
    </header>
  );
}
