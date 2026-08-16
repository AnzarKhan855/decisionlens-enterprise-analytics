"use client";

import React from "react";
import api from "@/lib/api";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderArchive,
  Bot,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Database,
  LineChart,
  Search,
  Upload,
  ShieldCheck,
  BarChart3,
  Building2,
  ChevronDown,
  TrendingUp,
  Target,
  Sliders,
} from "lucide-react";

interface SidebarProps {
  onClose?: () => void;
}

const NAVIGATION = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Workspaces", href: "/datasets", icon: FolderArchive },
  { name: "Upload", href: "/upload", icon: Upload },
  { name: "Copilot", href: "/copilot", icon: Bot },
  { name: "Forecasts", href: "/forecasts", icon: TrendingUp },
  { name: "Strategy", href: "/strategy", icon: Target },
  { name: "Scenario", href: "/scenario", icon: Sliders },
  { name: "3D Architecture", href: "/architecture", icon: BarChart3 },
  { name: "Search", href: "/search", icon: Search },
  { name: "Reports", href: "/reports", icon: FileText },
  { name: "Settings", href: "/settings", icon: Settings },
];

const ADMIN_LINKS = [
  { name: "Data Catalog", href: "/catalog", icon: Database },
  { name: "Lineage", href: "/lineage", icon: BarChart3 },
  { name: "Quality", href: "/data-quality", icon: ShieldCheck },
  { name: "Audit", href: "/audit", icon: LineChart },
];

interface WorkspaceItem {
  workspace_id: string;
  name: string;
  industry?: string;
}

export default function Sidebar({ onClose }: SidebarProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = React.useState(false);
  const [showAdmin, setShowAdmin] = React.useState(false);
  const [activeWorkspace, setActiveWorkspace] = React.useState("");
  const [workspaces, setWorkspaces] = React.useState<WorkspaceItem[]>([]);
  const [user, setUser] = React.useState<{ full_name?: string; email?: string; role?: string } | null>(null);

  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("decisionlens_user");
      if (stored) {
        try {
          setUser(JSON.parse(stored));
        } catch (e) {}
      }

      api.get("/auth/me")
        .then((res) => {
          if (res.data) {
            setUser(res.data);
            localStorage.setItem("decisionlens_user", JSON.stringify(res.data));
          }
        })
        .catch(() => {});

      api.get("/workspaces")
        .then((res) => {
          const data = res.data;
          if (data.workspaces && Array.isArray(data.workspaces) && data.workspaces.length > 0) {
            setWorkspaces(data.workspaces);
            const storedActive = localStorage.getItem("decisionlens_active_workspace");
            const activeId = storedActive && data.workspaces.some((w: WorkspaceItem) => w.workspace_id === storedActive)
              ? storedActive
              : data.active_workspace_id || data.workspaces[0].workspace_id;
            setActiveWorkspace(activeId);
          }
        })
        .catch((err) => {
          console.warn("[Sidebar] Failed to load workspaces", err);
        });
    }
  }, []);

  async function handleWorkspaceSelect(wsId: string) {
    if (!wsId || wsId === activeWorkspace) return;
    setActiveWorkspace(wsId);
    if (typeof window !== "undefined") {
      localStorage.setItem("decisionlens_active_workspace", wsId);
    }
    await api.post(`/workspaces/${wsId}/activate`).catch((err) => {
      console.warn("[Sidebar] Workspace activation failed", err);
    });
    window.location.reload();
  }

  const displayName = user?.full_name || user?.email?.split("@")[0] || "Enterprise User";
  const displayRole = user?.role ? user.role.replace("_", " ").toLowerCase() : "User";
  const initials = React.useMemo(() => {
    if (!user || !user.full_name) return "EU";
    const parts = user.full_name.trim().split(" ");
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return parts[0].substring(0, 2).toUpperCase();
  }, [user]);

  function handleNavClick() {
    if (onClose) onClose();
  }

  function handleLogout() {
    localStorage.removeItem("decisionlens_access_token");
    localStorage.removeItem("decisionlens_active_workspace");
    localStorage.removeItem("decisionlens_user");
    window.location.href = "/login";
  }

  return (
    <aside
      className={`
        sticky top-0 h-screen flex flex-col
         bg-surface border-r border-border-color text-text-primary
        overflow-y-auto z-40 select-none
        transition-all duration-300 ease-in-out
        ${collapsed ? "w-16" : "w-64"}
      `}
      role="navigation"
      aria-label="Primary navigation"
    >
      {/* Brand Header */}
      <div className="px-3 py-4 border-b border-border-color/80 flex items-center justify-between">
        {!collapsed && (
          <div className="flex items-center gap-3 animate-fade-in">
            <div
               className="h-9 w-9 rounded-xl bg-primary-600 flex items-center justify-center text-text-primary font-extrabold text-sm shadow-md shadow-primary-600/30 shrink-0"
              aria-hidden="true"
            >
              DL
            </div>
            <div className="min-w-0">
              <h1 className="text-sm font-bold tracking-tight text-text-primary truncate">DecisionLens</h1>
              <p className="text-[11px] text-text-muted font-medium">Enterprise Analytics</p>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="mx-auto" aria-hidden="true">
            <div className="h-9 w-9 rounded-xl bg-primary-600 flex items-center justify-center text-text-primary font-extrabold text-sm shadow-md shadow-primary-600/30">
              DL
            </div>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={`
            p-1.5 hover:bg-surface-muted rounded-lg text-text-muted hover:text-text-primary transition-colors duration-200
            ${collapsed ? "mx-auto mt-1" : ""}
          `}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Workspace Selector */}
      {!collapsed ? (
        workspaces.length > 0 && (
          <div className="px-3 py-3 border-b border-border-color/60">
            <label htmlFor="sidebar-workspace-select" className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-1.5 block">
              Workspace
            </label>
            <div className="relative">
              <select
                id="sidebar-workspace-select"
                value={activeWorkspace}
                onChange={(e) => handleWorkspaceSelect(e.target.value)}
                className="
                  w-full text-xs font-semibold text-text-secondary
                  bg-surface-muted/80 hover:bg-surface-muted
                  pl-2.5 pr-7 py-2 rounded-lg
                  border border-border-color/60
                  cursor-pointer outline-none
                  transition-all
                  focus-visible:ring-2 focus-visible:ring-primary-500
                  appearance-none
                "
                aria-label="Select active workspace"
              >
                 {workspaces.map((ws) => (
                  <option key={ws.workspace_id} value={ws.workspace_id} className="text-text-primary">
                    {ws.name} ({ws.industry || "Enterprise"})
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-text-muted absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" aria-hidden="true" />
            </div>
          </div>
        )
      ) : (
        <div className="px-2 py-3 border-b border-border-color/60 flex justify-center" title={workspaces.find(w => w.workspace_id === activeWorkspace)?.name ?? "Workspace"}>
          <div             className="p-2 bg-surface-muted/60 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-muted transition-colors duration-200 cursor-default">
            <Building2 className="w-4 h-4" aria-hidden="true" />
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-0.5" aria-label="Main navigation">
        {NAVIGATION.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              onClick={handleNavClick}
              className={`
                group relative flex items-center gap-3
                px-3 py-2.5 rounded-xl text-sm font-medium
                transition-all duration-200 ease-in-out active:scale-[0.98]
                 ${isActive
                    ? "bg-primary-600 text-white shadow-sm"
                    : "text-text-secondary hover:bg-surface-muted/60 hover:text-text-primary"
                  }
                ${collapsed ? "justify-center px-2" : ""}
              `}
              aria-current={isActive ? "page" : undefined}
              title={collapsed ? item.name : undefined}
            >
              <Icon
                className={`w-4 h-4 shrink-0 ${isActive ? "text-white" : "text-text-muted group-hover:text-text-secondary"}`}
                aria-hidden="true"
              />
              {!collapsed && <span className="truncate">{item.name}</span>}

              {/* Tooltip for collapsed state */}
              {collapsed && (
                <span
                  className="
                    absolute left-full ml-2 px-2.5 py-1.5
                    bg-surface-elevated text-text-primary text-xs font-medium
                    rounded-lg shadow-lg border border-border-strong
                    whitespace-nowrap pointer-events-none
                    opacity-0 group-hover:opacity-100
                    transition-opacity z-50
                  "
                  aria-hidden="true"
                >
                  {item.name}
                </span>
              )}
            </Link>
          );
        })}

        {/* Admin Section */}
        {!collapsed ? (
          <div className="pt-4 mt-4 border-t border-border-color/80">
              <button
                onClick={() => setShowAdmin(!showAdmin)}
                className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold uppercase tracking-wider text-text-muted hover:text-text-secondary transition-colors duration-200"
                aria-expanded={showAdmin}
                aria-controls="admin-nav-section"
              >
              <span>Administration</span>
              <ChevronRight className={`w-3.5 h-3.5 transition-transform duration-200 ${showAdmin ? "rotate-90" : ""}`} />
            </button>
            <div id="admin-nav-section" className={`mt-1.5 space-y-0.5 ${showAdmin ? "" : "hidden"}`}>
              {ADMIN_LINKS.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                   <Link
                     key={item.name}
                     href={item.href}
                     onClick={handleNavClick}
                     className={`
                       flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium
                       transition-all active:scale-[0.98]
                       ${isActive
                         ? "bg-surface-muted text-text-primary"
                         : "text-text-muted hover:bg-surface-muted/40 hover:text-text-secondary"
                       }
                     `}
                   >
                    <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                    <span className="truncate">{item.name}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="pt-4 mt-4 border-t border-border-color/80 flex flex-col items-center gap-1">
            {ADMIN_LINKS.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={handleNavClick}
                        className={`
                        group relative flex items-center justify-center
                        p-2.5 rounded-xl text-sm font-medium
                        transition-all duration-200 active:scale-[0.98]
                        ${isActive
                          ? "bg-surface-muted text-text-primary"
                          : "text-text-muted hover:bg-surface-muted/40 hover:text-text-secondary"
                        }
                    `}
                  title={item.name}
                >
                  <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                  <span
                    className="
                      absolute left-full ml-2 px-2.5 py-1.5
                    bg-surface-elevated text-text-primary text-xs font-medium
                    rounded-lg shadow-lg border border-border-strong
                      whitespace-nowrap pointer-events-none
                      opacity-0 group-hover:opacity-100
                      transition-opacity z-50
                    "
                    aria-hidden="true"
                  >
                    {item.name}
                  </span>
                </Link>
              );
            })}
          </div>
        )}
      </nav>

      {/* Footer — User + Status */}
       <div className="p-2.5 border-t border-border-color/80 bg-background/40 space-y-2">
          {/* System Health */}
          <div className={`flex items-center gap-2 text-xs text-text-muted ${collapsed ? "justify-center px-1" : "px-2"}`}>
            <span className="h-2 w-2 rounded-full bg-success-500 animate-pulse shrink-0" aria-hidden="true" />
            {!collapsed && (
              <span className="font-medium text-text-secondary truncate">System Healthy</span>
            )}
          {collapsed && (
            <span className="sr-only">System status: healthy</span>
          )}
        </div>

          {/* User Avatar + Role Badge */}
          {!collapsed ? (
            <div className="flex items-center gap-2.5 px-2 py-2 rounded-xl hover:bg-surface-muted/40 transition-colors">
              <div
                className="h-8 w-8 rounded-full bg-primary-600 text-text-primary font-bold text-xs flex items-center justify-center shadow-sm shrink-0"
                aria-hidden="true"
              >
                {initials}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-text-secondary truncate">{displayName}</p>
                <span className="inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-primary-500/20 text-primary-300 border border-primary-500/30 capitalize">
                  {displayRole}
                </span>
              </div>
            </div>
          ) : (
            <div className="flex justify-center py-1" title={`${displayName} · ${displayRole}`}>
               <div className="h-8 w-8 rounded-full bg-primary-600 text-text-primary font-bold text-xs flex items-center justify-center shadow-sm cursor-default">
                {initials}
              </div>
            </div>
          )}

          {/* Logout */}
          {!collapsed ? (
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-text-muted hover:bg-surface-muted/60 hover:text-text-primary transition-all duration-200"
              aria-label="Sign out"
            >
              <LogOut className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>Sign Out</span>
            </button>
          ) : (
            <div className="flex justify-center">
              <button
                onClick={handleLogout}
                className="p-2 text-text-muted hover:text-text-primary hover:bg-surface-muted/60 rounded-lg transition-all duration-200"
                aria-label="Sign out"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>
          )}
        </div>
    </aside>
  );
}
