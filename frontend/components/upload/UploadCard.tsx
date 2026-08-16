"use client";

import { useRef, useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { uploadMultipleDatasets, uploadDataset } from "@/lib/upload";
import api from "@/lib/api";
import { UploadCloud, CheckCircle2, AlertCircle, ArrowLeft, FileSpreadsheet, Folder, HardDrive, CornerLeftUp } from "lucide-react";

import { activateAndSyncWorkspace } from "@/lib/workspace-resolver";
import { invalidateCache } from "@/lib/api";

export default function UploadCard() {
  const inputRef = useRef<HTMLInputElement>(null);

  const [activeTab, setActiveTab] = useState<"upload" | "device">("upload");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [processedCount, setProcessedCount] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  // Device Browse state
  const [localPathInput, setLocalPathInput] = useState("");
  const [currentDir, setCurrentDir] = useState<string>("");
  const [parentDir, setParentDir] = useState<string | null>(null);
  const [dirItems, setDirItems] = useState<any[]>([]);
  const [browseLoading, setBrowseLoading] = useState(false);

  useEffect(() => {
    if (activeTab === "device") {
      fetchLocalDirectory();
    }
  }, [activeTab]);

  async function fetchLocalDirectory(path?: string) {
    try {
      setBrowseLoading(true);
      const url = path ? `/upload/local-browse?path=${encodeURIComponent(path)}` : "/upload/local-browse";
      const res = await api.get(url);
      setCurrentDir(res.data.current_directory);
      setParentDir(res.data.parent_directory);
      setDirItems(res.data.items || []);
    } catch (err: any) {
      console.error(err);
    } finally {
      setBrowseLoading(false);
    }
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const fileList = Array.from(files);

    try {
      setLoading(true);
      setSuccess(false);
      setErrorMsg("");

      let resultData: any = null;
      if (fileList.length === 1) {
        resultData = await uploadDataset(fileList[0]);
        setProcessedCount(1);
      } else {
        resultData = await uploadMultipleDatasets(fileList);
        setProcessedCount(resultData.processed_datasets?.length || fileList.length);
      }

      activateAndSyncWorkspace(resultData);
      invalidateCache();
      await api.get("/workspaces").catch((err) => {
        console.warn("[UploadCard] Failed to refresh workspaces", err);
      });
      await api.get("/workspace/active").catch((err) => {
        console.warn("[UploadCard] Failed to refresh active workspace", err);
      });

      setSuccess(true);
      setTimeout(() => {
        window.location.href = "/dynamic-dashboard";
      }, 800);
    } catch (error: any) {
      console.error(error);
      if (error.response?.status === 401) {
        setErrorMsg("Session expired or authentication required. Please log in again.");
      } else {
        setErrorMsg(error.response?.data?.detail || "Failed to process dataset files. Please check file formats.");
      }
    } finally {
      setLoading(false);
    }
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }

  async function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (!files || files.length === 0) return;

    const fileList = Array.from(files);
    const validFiles = fileList.filter((f) =>
      /\.(csv|xlsx|xls|parquet)$/i.test(f.name)
    );
    if (validFiles.length === 0) {
      setErrorMsg("No valid files detected. Please drop CSV, Excel, or Parquet files.");
      return;
    }

    try {
      setLoading(true);
      setSuccess(false);
      setErrorMsg("");

      let resultData: any = null;
      if (validFiles.length === 1) {
        resultData = await uploadDataset(validFiles[0]);
        setProcessedCount(1);
      } else {
        resultData = await uploadMultipleDatasets(validFiles);
        setProcessedCount(resultData.processed_datasets?.length || validFiles.length);
      }

      activateAndSyncWorkspace(resultData);
      invalidateCache();
      await api.get("/workspaces").catch((err) => {
        console.warn("[UploadCard] Failed to refresh workspaces", err);
      });

      setSuccess(true);
      setTimeout(() => {
        window.location.href = "/dynamic-dashboard";
      }, 800);
    } catch (error: any) {
      console.error(error);
      setErrorMsg(error.response?.data?.detail || "Failed to process dropped files.");
    } finally {
      setLoading(false);
    }
  }

  async function handleImportLocalPath(pathToImport?: string) {
    const targetPath = pathToImport || localPathInput.trim();
    if (!targetPath) {
      setErrorMsg("Please enter a valid file path on your device.");
      return;
    }

    try {
      setLoading(true);
      setSuccess(false);
      setErrorMsg("");

      const res = await api.post("/upload/local-path", { file_path: targetPath });
      activateAndSyncWorkspace(res.data);
      invalidateCache();
      await api.get("/workspaces").catch((err) => {
        console.warn("[UploadCard] Failed to refresh workspaces", err);
      });
      await api.get("/workspace/active").catch((err) => {
        console.warn("[UploadCard] Failed to refresh active workspace", err);
      });

      setProcessedCount(1);
      setSuccess(true);

      setTimeout(() => {
        window.location.href = "/dynamic-dashboard";
      }, 800);
    } catch (error: any) {
      console.error(error);
      setErrorMsg(error.response?.data?.detail || "Failed to access file path on device.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="premium-card p-8 space-y-6"
    >
      {/* Top Header & Navigation Button */}
      <div className="flex items-center justify-between border-b border-border-light pb-4">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-primary-600">
            Enterprise Ingestion Portal
          </span>
          <h2 className="text-xl font-bold text-text-primary mt-0.5">Device File & Dataset Ingestion</h2>
        </div>
        <Link
          href="/datasets"
          className="px-4 py-2 bg-surface-muted hover:bg-border-color text-text-primary text-xs font-semibold rounded-xl transition-colors flex items-center gap-2 border border-border-color"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Dataset Library</span>
        </Link>
      </div>

      {/* Tabs: Drag & Drop vs Local Device Browser */}
      <div className="flex flex-wrap items-center gap-2 bg-surface-muted p-1.5 rounded-xl text-xs font-semibold">
        <button
          onClick={() => setActiveTab("upload")}
          className={`flex-1 py-2 px-3 rounded-lg transition-all flex items-center justify-center gap-2 ${
            activeTab === "upload"
              ? "bg-surface text-primary-600 shadow-sm"
              : "text-text-secondary hover:text-text-primary"
          }`}
        >
          <UploadCloud className="w-4 h-4" />
          <span>Drag & Drop Upload</span>
        </button>

        <button
          onClick={() => setActiveTab("device")}
          className={`flex-1 py-2 px-3 rounded-lg transition-all flex items-center justify-center gap-2 ${
            activeTab === "device"
              ? "bg-surface text-primary-600 shadow-sm"
              : "text-text-secondary hover:text-text-primary"
          }`}
        >
          <HardDrive className="w-4 h-4" />
          <span>Device Folder Browser</span>
        </button>
      </div>

      {/* Tab 1: Drag & Drop Multi-Upload Zone */}
      {activeTab === "upload" && (
        <motion.div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          animate={{
            scale: isDragging ? 1.015 : 1,
            borderColor: isDragging ? "var(--primary-500)" : undefined,
            backgroundColor: isDragging ? "rgba(99,102,241,0.06)" : undefined,
          }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className={`border-2 border-dashed border-border-color rounded-2xl p-12 text-center cursor-pointer transition-all duration-200 group flex flex-col items-center justify-center space-y-3 ${
             isDragging
               ? "border-primary-500 bg-primary-50/40"
               : "hover:border-primary-300 hover:bg-primary-50/50"
          }`}
        >
           <div className="w-16 h-16 rounded-2xl bg-primary-50 text-primary-600 group-hover:scale-110 group-hover:bg-primary-600 group-hover:text-primary-100 transition-all flex items-center justify-center shadow-sm">
            <UploadCloud className="w-8 h-8" />
          </div>

          <div>
            <h3 className="text-lg font-bold text-text-primary group-hover:text-primary-600 transition-colors">
              Drop multiple CSV, Excel, or Parquet files here
            </h3>
            <p className="text-xs text-text-muted mt-1">
              Click to select any files from your device folders. Supports batch processing up to 2GB per file.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-text-muted bg-surface-muted px-3 py-1.5 rounded-lg border border-border-color">
            <FileSpreadsheet className="w-3.5 h-3.5 text-primary-500" />
            <span>High-Performance Data Processing & Analysis</span>
          </div>

          <AnimatePresence>
            {isDragging && (
              <motion.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="px-4 py-2 bg-primary-600 text-white text-xs font-bold rounded-full shadow-lg"
              >
                Drop files to upload
              </motion.div>
            )}
          </AnimatePresence>

          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".csv,.xlsx,.xls,.parquet"
            className="hidden"
            onChange={handleFileChange}
          />
        </motion.div>
      )}

      {/* Tab 2: Local Device Path & Folder Browser */}
      {activeTab === "device" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Paste absolute file path (e.g., C:\Users\anzar\Documents\dataset.csv)..."
              value={localPathInput}
              onChange={(e) => setLocalPathInput(e.target.value)}
              className="flex-1 px-4 py-2.5 bg-surface-muted border border-border-color rounded-xl text-xs text-text-primary outline-none focus:border-primary-500 font-mono"
            />
            <button
              onClick={() => handleImportLocalPath()}
              className="px-5 py-2.5 bg-primary-600 hover:bg-primary-700 text-white text-xs font-semibold rounded-xl transition-all shadow-md shadow-primary-600/30 flex items-center gap-2"
            >
              <HardDrive className="w-4 h-4" />
              <span>Import Path</span>
            </button>
          </div>

          {/* Folder Explorer */}
          <div className="bg-surface-muted border border-border-color rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between text-xs border-b border-border-color pb-2">
              <span className="font-mono text-text-secondary font-semibold truncate max-w-lg">
                Directory: {currentDir}
              </span>
              {parentDir && (
                <button
                  onClick={() => fetchLocalDirectory(parentDir)}
                  className="px-2.5 py-1 bg-surface hover:bg-border-color text-text-primary rounded-lg text-xs font-medium border border-border-color flex items-center gap-1"
                >
                  <CornerLeftUp className="w-3.5 h-3.5" />
                  <span>Up Folder</span>
                </button>
              )}
            </div>

            {browseLoading ? (
              <div className="text-center py-6 text-xs text-text-muted">Reading directory contents...</div>
            ) : dirItems.length === 0 ? (
              <div className="text-center py-6 text-xs text-text-muted">No datasets or subfolders found in this directory.</div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-60 overflow-y-auto pr-1">
                {dirItems.map((item, idx) => (
                  <div
                    key={idx}
                    onClick={() => {
                      if (item.type === "folder") {
                        fetchLocalDirectory(item.path);
                      } else {
                        handleImportLocalPath(item.path);
                      }
                    }}
                    className={`p-2.5 rounded-lg border text-xs flex items-center gap-2.5 cursor-pointer transition-all ${
                      item.type === "folder"
                        ? "bg-surface hover:bg-primary-50/60 border-border-color text-text-primary"
                        : "bg-success-50/50 hover:bg-success-100/70 border-success-200 text-success-800 font-semibold"
                    }`}
                  >
                    {item.type === "folder" ? (
                      <Folder className="w-4 h-4 text-primary-500 flex-shrink-0" />
                    ) : (
                      <FileSpreadsheet className="w-4 h-4 text-success-600 flex-shrink-0" />
                    )}
                    <span className="truncate flex-1 font-mono">{item.name}</span>
                    {item.type === "file" && (
                      <span className="px-1.5 py-0.5 bg-success-200 text-success-800 text-[10px] rounded font-bold">
                        IMPORT
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Status Feedback */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex items-center justify-center gap-3 p-4 bg-primary-50 text-primary-700 rounded-xl border border-primary-100 text-xs font-semibold"
          >
            <motion.div
              className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full"
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 0.9, ease: "linear" }}
            />
            <span>Processing your data...</span>
          </motion.div>
        )}

        {success && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="flex items-center justify-center gap-2 p-4 bg-success-50 text-success-700 rounded-xl border border-success-200 text-xs font-semibold"
          >
            <CheckCircle2 className="w-4 h-4 text-success-600" />
            <span>{processedCount} dataset(s) loaded successfully! Launching intelligence dashboard...</span>
          </motion.div>
        )}

        {errorMsg && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex items-center justify-center gap-2 p-4 bg-error-50 text-error-700 rounded-xl border border-error-200 text-xs font-semibold"
          >
            <AlertCircle className="w-4 h-4 text-error-600" />
            <span>{errorMsg}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}