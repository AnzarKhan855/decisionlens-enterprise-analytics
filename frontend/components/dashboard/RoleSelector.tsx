"use client";

import React from "react";
import { UserCheck, Shield, DollarSign, Activity, ShoppingCart, Users, Truck } from "lucide-react";

export type ExecutiveRole = "CEO" | "CFO" | "COO" | "CMO" | "CTO" | "Sales Manager" | "HR" | "Supply Chain";

interface RoleSelectorProps {
  selectedRole: ExecutiveRole;
  onSelectRole: (role: ExecutiveRole) => void;
}

const ROLES: { role: ExecutiveRole; icon: any; label: string }[] = [
  { role: "CEO", icon: Shield, label: "Chief Executive (CEO)" },
  { role: "CFO", icon: DollarSign, label: "Chief Financial (CFO)" },
  { role: "COO", icon: Activity, label: "Chief Operations (COO)" },
  { role: "CMO", icon: ShoppingCart, label: "Chief Marketing (CMO)" },
  { role: "HR", icon: Users, label: "Human Resources (HR)" },
  { role: "Supply Chain", icon: Truck, label: "Supply Chain Manager" },
];

export default function RoleSelector({ selectedRole, onSelectRole }: RoleSelectorProps) {
  return (
    <div className="premium-card p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div className="flex items-center gap-2">
        <div className="p-2 bg-primary-50 text-primary-600 rounded-xl">
          <UserCheck className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-primary-600">Executive Perspective Selector</h3>
          <p className="text-sm font-semibold text-text-primary">Tailor Dashboard KPIs & Recommendations for Your Role</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {ROLES.map((r) => {
          const Icon = r.icon;
          const isActive = selectedRole === r.role;
          return (
            <button
              key={r.role}
              onClick={() => onSelectRole(r.role)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                isActive
                  ? "bg-primary-600 text-white shadow-md shadow-primary-600/30"
                  : "bg-surface-muted text-text-secondary hover:bg-border-color border border-border-color"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{r.role}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
