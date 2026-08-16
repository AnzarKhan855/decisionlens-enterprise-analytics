import api from "./api";
import type { DashboardPayload } from "./types";

export async function getDynamicDashboard(explicitWsId?: string): Promise<DashboardPayload> {
    const wsId = explicitWsId || (typeof window !== "undefined"
        ? localStorage.getItem("decisionlens_active_workspace")
        : null);
    const params: Record<string, string> = {};
    if (wsId) {
        params.workspace_id = wsId;
    }
    const response = await api.get("/dashboard/dynamic", { params });
    return response.data as DashboardPayload;
}