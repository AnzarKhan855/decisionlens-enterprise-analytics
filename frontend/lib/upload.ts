import api from "./api";

export async function uploadDataset(file: File, workspaceId?: string) {
  const formData = new FormData();
  formData.append("file", file);
  if (workspaceId) {
    formData.append("workspace_id", workspaceId);
  }

  const response = await api.post("/upload/", formData);
  return response.data;
}

export async function uploadMultipleDatasets(files: File[], workspaceId?: string) {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });
  if (workspaceId) {
    formData.append("workspace_id", workspaceId);
  }

  const response = await api.post("/upload/batch", formData);
  return response.data;
}

export async function uploadZipWorkspace(file: File, workspaceName?: string) {
  const formData = new FormData();
  formData.append("file", file);
  if (workspaceName) {
    formData.append("workspace_name", workspaceName);
  }

  const response = await api.post("/workspace/upload-zip", formData);
  return response.data;
}

export async function uploadFolderWorkspace(files: FileList | File[], workspaceName?: string) {
  const formData = new FormData();
  const fileArray = Array.from(files);
  fileArray.forEach((file) => {
    formData.append("files", file);
  });
  if (workspaceName) {
    formData.append("workspace_name", workspaceName);
  }

  const response = await api.post("/workspace/upload-folder", formData);
  return response.data;
}