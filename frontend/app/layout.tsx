import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import AppShell from "@/components/layout/AppShell";
import { ToastProvider } from "@/lib/toast";
import { ThemeProvider } from "@/components/theme/ThemeProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DecisionLens | Enterprise Decision Intelligence",
  description: "AI-powered enterprise analytics platform transforming business data into actionable insights.",
  keywords: [
    "Analytics",
    "Business Intelligence",
    "Decision Intelligence",
    "AI Analytics",
    "Data Platform"
  ],
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} min-h-screen bg-background text-text-primary font-sans antialiased`}>
        <ThemeProvider>
          <ToastProvider>
            <a href="#main-content" className="skip-link">
              Skip to main content
            </a>
            <AppShell>{children}</AppShell>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
