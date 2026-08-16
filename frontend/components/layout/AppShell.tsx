"use client";

import React, { useState } from "react";
import { usePathname } from "next/navigation";
import Sidebar from "./Sidebar";
import Header from "./Header";

const PUBLIC_ROUTES = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-otp",
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublic = PUBLIC_ROUTES.includes(pathname);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  if (isPublic) {
    return (
      <main id="main-content" className="min-h-screen" tabIndex={-1}>
        {children}
      </main>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Desktop Sidebar */}
      <aside
        className="hidden lg:block fixed left-0 top-0 h-screen z-40"
        aria-label="Main navigation"
      >
        <Sidebar />
      </aside>

      {/* Mobile Sidebar Backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-background/60 backdrop-blur-sm z-40 lg:hidden animate-fade-in"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile Sidebar */}
      {mobileMenuOpen && (
        <aside
          className="fixed left-0 top-0 h-screen z-50 lg:hidden animate-slide-up"
          aria-label="Mobile navigation"
        >
          <Sidebar onClose={() => setMobileMenuOpen(false)} />
        </aside>
      )}

      {/* Main Content Wrapper */}
      <div className="flex-1 lg:ml-64 flex flex-col min-w-0 h-screen transition-all duration-300">
        <Header onMobileMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)} />
        <main
          id="main-content"
          className="flex-1 overflow-y-auto"
          role="main"
          aria-label="Main content"
          tabIndex={-1}
        >
          <div className="max-w-7xl mx-auto w-full px-4 lg:px-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
