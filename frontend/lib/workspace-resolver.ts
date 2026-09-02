import { getCached, apiPost, invalidateCache } from "./api";

export interface Workspace {
  workspace_id: string;
  name: string;
  industry?: string;
  is_active?: boolean;
  tables?: any[];
}

export function activateAndSyncWorkspace(data: any): string | null {
  if (typeof window === "undefined") return null;

  const wsId =
    data?.workspace_id ||
    data?.active_workspace ||
    data?.workspace?.workspace_id ||
    data?.data?.workspace_id;

  if (wsId) {
    localStorage.setItem("decisionlens_active_workspace", wsId);
    localStorage.setItem("decisionlens_user_workspace", wsId);
    window.dispatchEvent(new CustomEvent("decisionlens:workspace_changed", { detail: { workspace_id: wsId } }));
  }

  // Purge stale in-memory API cache after upload or activation
  invalidateCache();

  return wsId || localStorage.getItem("decisionlens_active_workspace");
}

export async function resolveActiveWorkspace(): Promise<Workspace | null> {
  if (typeof window === "undefined") return null;

  const legacyKeys = ["workspaceId", "activeWorkspace", "currentWorkspace", "active_ws_id"];
  legacyKeys.forEach((key) => {
    localStorage.removeItem(key);
  });

  const storedId = localStorage.getItem("decisionlens_active_workspace");

  try {
    if (storedId) {
      try {
        const res = await apiPost<{ success: boolean; workspace?: Workspace }>(
          `/workspaces/${storedId}/activate`
        );
        if (res && res.success && res.workspace) {
          invalidateCache();
          localStorage.setItem("decisionlens_active_workspace", res.workspace.workspace_id);
          localStorage.setItem("decisionlens_user_workspace", res.workspace.workspace_id);
          return res.workspace;
        }
      } catch (err) {
        console.warn("[WorkspaceResolver] Activation failed for stored workspace", storedId, err);
      }
      localStorage.removeItem("decisionlens_active_workspace");
      localStorage.removeItem("decisionlens_user_workspace");
      invalidateCache();
      return null;
    }

    const res = await getCached<any>("/workspace/active", undefined, 0).catch((err) => {
      console.warn("[WorkspaceResolver] getCached /workspace/active failed", err);
      return null;
    });
    if (res && res.workspace) {
      const validWs = res.workspace;
      localStorage.setItem("decisionlens_active_workspace", validWs.workspace_id);
      localStorage.setItem("decisionlens_user_workspace", validWs.workspace_id);
      return validWs;
    }

    const listRes = await getCached<any>("/workspaces", undefined, 0).catch((err) => {
      console.warn("[WorkspaceResolver] getCached /workspaces failed", err);
      return null;
    });
      const matched =
        listRes.workspaces.find((w: any) => w.workspace_id === storedId) ||
        listRes.workspaces.find((w: any) => w.is_active) ||
        listRes.workspaces.find((w: any) => w.workspace_id === listRes.active_workspace_id) ||
        (listRes.workspaces.length > 0 ? listRes.workspaces[0] : null);
      if (matched) {
        try {
          const actRes = await apiPost<{ success: boolean; workspace?: Workspace }>(
            `/workspaces/${matched.workspace_id}/activate`
          );
          if (actRes && actRes.success && actRes.workspace) {
            localStorage.setItem("decisionlens_active_workspace", matched.workspace_id);
            localStorage.setItem("decisionlens_user_workspace", matched.workspace_id);
            return matched;
          }
        } catch (err) {
          console.warn("[WorkspaceResolver] Activation failed", err);
        }
      }

    localStorage.removeItem("decisionlens_active_workspace");
    localStorage.removeItem("decisionlens_user_workspace");
    invalidateCache();
    return null;
  } catch (err) {
    localStorage.removeItem("decisionlens_active_workspace");
    localStorage.removeItem("decisionlens_user_workspace");
    invalidateCache();
    return null;
  }
}
