"use client";

import React, { useState, useCallback, useEffect } from "react";
import {
  Settings,
  Shield,
  Bell,
  Key,
  CheckCircle2,
  User,
  Lock,
  Monitor,
  Building2,
  Palette,
} from "lucide-react";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Select from "@/components/ui/Select";
import { useTheme } from "@/components/theme/ThemeProvider";

type TabId = "profile" | "security" | "api-keys" | "notifications" | "theme" | "workspace" | "organization";

interface TabItem {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const TABS: TabItem[] = [
  { id: "profile", label: "Profile", icon: <User className="w-4 h-4" /> },
  { id: "security", label: "Security", icon: <Shield className="w-4 h-4" /> },
  { id: "api-keys", label: "API Keys", icon: <Key className="w-4 h-4" /> },
  { id: "notifications", label: "Notifications", icon: <Bell className="w-4 h-4" /> },
  { id: "theme", label: "Theme", icon: <Palette className="w-4 h-4" /> },
  { id: "workspace", label: "Workspace", icon: <Building2 className="w-4 h-4" /> },
  { id: "organization", label: "Organization", icon: <Building2 className="w-4 h-4" /> },
];

const MOCK_API_KEYS = [
  { id: "1", name: "Production Analytics", created: "2026-07-12", lastUsed: "2 hours ago" },
  { id: "2", name: "CI/CD Pipeline", created: "2026-06-28", lastUsed: "1 day ago" },
  { id: "3", name: "Development Test", created: "2026-05-15", lastUsed: "Never" },
];

const MOCK_SESSIONS = [
  { id: "1", device: "MacBook Pro", location: "San Francisco, CA", active: true, lastActive: "Now" },
  { id: "2", device: "iPhone 15", location: "San Francisco, CA", active: false, lastActive: "2 hours ago" },
  { id: "3", device: "Windows Desktop", location: "New York, NY", active: false, lastActive: "3 days ago" },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("profile");
  const [saved, setSaved] = useState(false);
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false);
  const [notifications, setNotifications] = useState({ email: true, push: true, weekly: false });

  useEffect(() => {
    let timerId: ReturnType<typeof setTimeout> | null = null;
    if (saved) {
      timerId = setTimeout(() => setSaved(false), 2000);
    }
    return () => {
      if (timerId) clearTimeout(timerId);
    };
  }, [saved]);

  function handleSave() {
    setSaved(true);
  }

  function handleThemeChange(value: string) {
    setTheme(value as "light" | "dark" | "system");
  }

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-5xl mx-auto">
      <div className="premium-card p-5 lg:p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary-600 mb-1">
            <Settings className="w-4 h-4" /> System Configuration
          </div>
          <h1 className="text-2xl font-extrabold text-text-primary">Enterprise Settings</h1>
          <p className="text-sm text-text-muted mt-1">Manage account, security, and workspace preferences.</p>
        </div>
        <Button onClick={handleSave} icon={<CheckCircle2 className="w-4 h-4" />}>
          Save Changes
        </Button>
      </div>

      {saved && (
        <div className="p-4 bg-success-50 text-success-700 text-xs font-semibold rounded-xl border border-success-200 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-success-600" />
          <span>Settings saved successfully.</span>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="premium-card overflow-hidden">
        <nav className="flex overflow-x-auto border-b border-border-color" aria-label="Settings tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center gap-2 px-5 py-3.5 text-xs font-semibold whitespace-nowrap
                transition-all cursor-pointer border-b-2 -mb-px
                ${activeTab === tab.id
                  ? "border-primary-600 text-primary-600 bg-primary-50/50"
                  : "border-transparent text-text-muted hover:text-text-secondary hover:bg-surface-muted"
                }
              `}
              aria-current={activeTab === tab.id ? "page" : undefined}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>

        <div className="p-6">
          {activeTab === "profile" && (
            <div className="space-y-6">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-primary-600 text-white font-extrabold text-xl flex items-center justify-center shadow-lg shadow-primary-600/30">
                  AK
                </div>
                <div>
                  <h3 className="text-sm font-extrabold text-text-primary">Anzar Khan</h3>
                  <p className="text-xs text-text-muted">anzar@enterprise.com</p>
                  <p className="text-xs text-primary-600 font-semibold">Super Admin</p>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Full Name" defaultValue="Anzar Khan" />
                <Input label="Email" type="email" defaultValue="anzar@enterprise.com" />
                <Input label="Role" defaultValue="Super Admin" disabled />
                <Input label="Phone" placeholder="+1 (555) 000-0000" />
              </div>
            </div>
          )}

          {activeTab === "security" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Current Password" type="password" />
                <Input label="New Password" type="password" />
                <Input label="Confirm Password" type="password" />
              </div>

              <div className="flex items-center justify-between p-4 bg-surface-muted rounded-xl border border-border-color">
                <div className="flex items-center gap-3">
                  <Lock className="w-5 h-5 text-primary-600" />
                  <div>
                    <p className="text-xs font-semibold text-text-primary">Two-Factor Authentication</p>
                    <p className="text-[11px] text-text-muted">Add an extra layer of security to your account</p>
                  </div>
                </div>
                <button
                  onClick={() => setTwoFactorEnabled(!twoFactorEnabled)}
                  className={`
                    relative w-11 h-6 rounded-full transition-colors cursor-pointer
                    ${twoFactorEnabled ? "bg-primary-600" : "bg-border-strong"}
                  `}
                  role="switch"
                  aria-checked={twoFactorEnabled}
                  aria-label="Toggle two-factor authentication"
                >
                  <span
                    className={`
                      absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-surface shadow-sm transition-transform
                      ${twoFactorEnabled ? "translate-x-5" : "translate-x-0"}
                    `}
                  />
                </button>
              </div>

              <div>
                <h4 className="text-xs font-semibold text-text-secondary mb-3">Active Sessions</h4>
                <div className="space-y-2">
                  {MOCK_SESSIONS.map((session) => (
                    <div key={session.id} className="flex items-center justify-between p-3 bg-surface-muted rounded-xl border border-border-color">
                      <div className="flex items-center gap-3">
                        <Monitor className="w-4 h-4 text-text-muted" aria-hidden="true" />
                        <div>
                          <p className="text-xs font-semibold text-text-primary">{session.device}</p>
                          <p className="text-[11px] text-text-muted">{session.location} · {session.lastActive}</p>
                        </div>
                      </div>
                      {session.active ? (
                        <span className="text-[11px] font-semibold text-success-600 bg-success-50 px-2 py-1 rounded-lg">Active</span>
                      ) : (
                        <button className="text-[11px] font-semibold text-error-600 hover:text-error-700 px-2 py-1 rounded-lg hover:bg-error-50 transition-colors">
                          Revoke
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "api-keys" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-semibold text-text-secondary">API Keys</h4>
                  <p className="text-[11px] text-text-muted">Manage keys for external integrations</p>
                </div>
                <Button size="sm" variant="primary">Create New Key</Button>
              </div>
              <div className="space-y-2">
                {MOCK_API_KEYS.map((key) => (
                  <div key={key.id} className="flex items-center justify-between p-4 bg-surface-muted rounded-xl border border-border-color">
                    <div className="flex items-center gap-3">
                      <Key className="w-4 h-4 text-primary-600" aria-hidden="true" />
                      <div>
                        <p className="text-xs font-semibold text-text-primary">{key.name}</p>
                        <p className="text-[11px] text-text-muted">Created {key.created} · Last used {key.lastUsed}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="p-2 rounded-lg hover:bg-surface-muted text-text-muted hover:text-primary-600 transition-colors" aria-label={`Copy key ${key.name}`}>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                      </button>
                      <button className="p-2 rounded-lg hover:bg-error-50 text-text-muted hover:text-error-600 transition-colors" aria-label={`Revoke key ${key.name}`}>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "notifications" && (
            <div className="space-y-4">
              {(["email", "push", "weekly"] as const).map((channel) => (
                <div key={channel} className="flex items-center justify-between p-4 bg-surface-muted rounded-xl border border-border-color">
                  <div>
                    <p className="text-xs font-semibold text-text-primary capitalize">{channel} Notifications</p>
                    <p className="text-[11px] text-text-muted">
                      {channel === "email" && "Receive updates via email"}
                      {channel === "push" && "Receive browser push notifications"}
                      {channel === "weekly" && "Receive weekly summary reports"}
                    </p>
                  </div>
                  <button
                    onClick={() => setNotifications({ ...notifications, [channel]: !notifications[channel] })}
                    className={`
                      relative w-11 h-6 rounded-full transition-colors cursor-pointer
                      ${notifications[channel] ? "bg-primary-600" : "bg-border-strong"}
                    `}
                    role="switch"
                    aria-checked={notifications[channel]}
                    aria-label={`Toggle ${channel} notifications`}
                  >
                    <span
                      className={`
                        absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-surface shadow-sm transition-transform
                        ${notifications[channel] ? "translate-x-5" : "translate-x-0"}
                      `}
                    />
                  </button>
                </div>
              ))}
            </div>
          )}

          {activeTab === "theme" && (
            <div className="space-y-4">
              <h4 className="text-xs font-semibold text-text-secondary">Appearance</h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  { value: "light", label: "Light", desc: "Bright and clean" },
                  { value: "dark", label: "Dark", desc: "Easy on the eyes" },
                  { value: "system", label: "System", desc: "Follow device setting" },
                ].map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handleThemeChange(option.value)}
                    className={`
                      p-4 rounded-xl border-2 text-left transition-all cursor-pointer
                      ${theme === option.value
                        ? "border-primary-600 bg-primary-50/50"
                        : "border-border-color hover:border-border-strong"
                      }
                    `}
                    aria-pressed={theme === option.value}
                  >
                    <p className="text-xs font-extrabold text-text-primary">{option.label}</p>
                    <p className="text-[11px] text-text-muted mt-0.5">{option.desc}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {activeTab === "workspace" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Workspace Name" defaultValue="DecisionLens Enterprise" />
                <Select
                  label="Default View"
                  options={[
                    { value: "dashboard", label: "Dashboard" },
                    { value: "reports", label: "Reports" },
                    { value: "explorer", label: "Data Explorer" },
                  ]}
                  value="dashboard"
                  onChange={() => {}}
                />
                <Select
                  label="Data Refresh Interval"
                  options={[
                    { value: "realtime", label: "Real-time" },
                    { value: "hourly", label: "Hourly" },
                    { value: "daily", label: "Daily" },
                  ]}
                  value="daily"
                  onChange={() => {}}
                />
                <Select
                  label="Default Date Range"
                  options={[
                    { value: "7d", label: "Last 7 days" },
                    { value: "30d", label: "Last 30 days" },
                    { value: "90d", label: "Last 90 days" },
                    { value: "1y", label: "Last 1 year" },
                  ]}
                  value="30d"
                  onChange={() => {}}
                />
              </div>
              <div className="p-4 bg-warning-50 border border-warning-100 rounded-xl text-xs text-warning-800">
                Workspace settings affect all team members. Changes may take a few minutes to propagate.
              </div>
            </div>
          )}

          {activeTab === "organization" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Organization Name" defaultValue="DecisionLens Enterprise" />
                <Select
                  label="Industry"
                  options={[
                    { value: "retail", label: "Retail" },
                    { value: "finance", label: "Finance" },
                    { value: "healthcare", label: "Healthcare" },
                    { value: "technology", label: "Technology" },
                    { value: "manufacturing", label: "Manufacturing" },
                  ]}
                  value="technology"
                  onChange={() => {}}
                />
                <Input label="Organization Size" placeholder="e.g. 50-200 employees" />
                <Input label="Website" placeholder="https://example.com" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-text-secondary mb-3">Members</h4>
                <div className="space-y-2">
                  {[
                    { name: "Anzar Khan", email: "anzar@enterprise.com", role: "Super Admin" },
                    { name: "Sarah Chen", email: "sarah@enterprise.com", role: "Org Admin" },
                    { name: "James Wilson", email: "james@enterprise.com", role: "Employee" },
                  ].map((member, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-surface-muted rounded-xl border border-border-color">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary-100 text-primary-700 text-xs font-bold flex items-center justify-center">
                          {member.name.split(" ").map(n => n[0]).join("")}
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-text-primary">{member.name}</p>
                          <p className="text-[11px] text-text-muted">{member.email}</p>
                        </div>
                      </div>
                      <span className="text-[11px] font-semibold text-text-muted bg-surface px-2 py-1 rounded-lg border border-border-color">{member.role}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
