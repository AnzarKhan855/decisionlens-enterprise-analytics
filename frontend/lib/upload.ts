import api from "./api";

export interface IngestionJob {
  job_id: string;
  workspace_id: string;
  dataset_id: string;
  filename: string;
  status: "CREATED" | "UPLOADING" | "UPLOADED" | "VALIDATING" | "PROCESSING" | "PROFILING" | "BUILDING_SEMANTIC_MODEL" | "READY" | "COMPLETED" | "SEMANTIC_READY" | "FAILED" | "CANCELLED";
  current_stage: string;
  progress_pct: number;
  message: string;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  error?: {
    failed_stage?: string;
    exception_class?: string;
    message?: string;
    suggested_fix?: string;
  } | null;
  metrics?: {
    rows?: number;
    columns?: number;
    health_score?: number;
    domain?: string;
    total_duration_ms?: number;
    stage_timings_ms?: Record<string, number>;
  };
  steps?: Array<{
    step: string;
    status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
    pct?: number;
  }>;
}

export async function uploadDataset(
  file: File,
  workspaceId?: string,
  onUploadProgress?: (percentCompleted: number) => void
): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);
  if (workspaceId) {
    formData.append("workspace_id", workspaceId);
  }

  const response = await api.post("/upload/", formData, {
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onUploadProgress) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onUploadProgress(percentCompleted);
      }
    },
  });
  return response.data;
}

export async function uploadMultipleDatasets(
  files: File[],
  workspaceId?: string,
  onUploadProgress?: (percentCompleted: number) => void
): Promise<any> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });
  if (workspaceId) {
    formData.append("workspace_id", workspaceId);
  }

  const response = await api.post("/upload/batch", formData, {
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onUploadProgress) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onUploadProgress(percentCompleted);
      }
    },
  });
  return response.data;
}

export async function uploadZipWorkspace(
  file: File,
  workspaceName?: string,
  onUploadProgress?: (percentCompleted: number) => void
): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);
  if (workspaceName) {
    formData.append("workspace_name", workspaceName);
  }

  const response = await api.post("/workspace/upload-zip", formData, {
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onUploadProgress) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onUploadProgress(percentCompleted);
      }
    },
  });
  return response.data;
}

export async function uploadFolderWorkspace(
  files: FileList | File[],
  workspaceName?: string,
  onUploadProgress?: (percentCompleted: number) => void
): Promise<any> {
  const formData = new FormData();
  const fileArray = Array.from(files);
  fileArray.forEach((file) => {
    formData.append("files", file);
  });
  if (workspaceName) {
    formData.append("workspace_name", workspaceName);
  }

  const response = await api.post("/workspace/upload-folder", formData, {
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onUploadProgress) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onUploadProgress(percentCompleted);
      }
    },
  });
  return response.data;
}

export async function getJobStatus(jobId: string): Promise<IngestionJob> {
  const res = await api.get(`/upload/status/${jobId}`);
  return res.data;
}

export async function getWorkspaceProcessingStatus(workspaceId: string): Promise<any> {
  const res = await api.get(`/workspace/${workspaceId}/status`);
  return res.data;
}

export async function cancelJob(jobId: string): Promise<any> {
  const res = await api.post(`/upload/cancel/${jobId}`);
  return res.data;
}