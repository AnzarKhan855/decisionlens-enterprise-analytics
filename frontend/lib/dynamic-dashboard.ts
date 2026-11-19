import api, { getCached } from "./api";
import type { DashboardPayload } from "./types";

export async function getDynamicDashboard(explicitWsId?: string, forceRefresh: boolean = false): Promise<DashboardPayload> {
    const wsId = explicitWsId || (typeof window !== "undefined"
        ? localStorage.getItem("decisionlens_active_workspace")
        : null);
    const params: Record<string, string> = {};
    if (wsId) {
        params.workspace_id = wsId;
    }
    if (forceRefresh) {
        const response = await api.get("/dashboard/dynamic", { params });
        return response.data as DashboardPayload;
    }
    return getCached<DashboardPayload>("/dashboard/dynamic", params, 60000);
}