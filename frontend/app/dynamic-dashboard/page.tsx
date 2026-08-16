import DynamicDashboardShell from "@/components/dashboard/DynamicDashboardShell";

export const dynamic = 'force-dynamic';

export default function DynamicDashboardPage() {
  return <DynamicDashboardShell />;
}

export const metadata = {
  title: "Executive Dashboard | DecisionLens",
  description: "AI-powered executive dashboard with KPIs, trends, predictions, and recommendations.",
};
