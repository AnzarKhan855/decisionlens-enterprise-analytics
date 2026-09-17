"use client";

import { useRef, useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { uploadMultipleDatasets, uploadDataset, getJobStatus, cancelJob, IngestionJob } from "@/lib/upload";
import api from "@/lib/api";
import {
  UploadCloud, CheckCircle2, AlertCircle, ArrowLeft, FileSpreadsheet,
  Folder, HardDrive, CornerLeftUp, RefreshCw, XCircle, Clock
} from "lucide-react";

import { activateAndSyncWorkspace } from "@/lib/workspace-resolver";
import { invalidateCache } from "@/lib/api";

export default function UploadCard() {
  const inputRef = useRef<HTMLInputElement>(null);

  const [activeTab, setActiveTab] = useState<"upload" | "device">("upload");
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [currentJob, setCurrentJob] = useState<IngestionJob | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
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

  async function startJobPolling(jobId: string, initialData: any) {
    const startTime = Date.now();
    setElapsedSeconds(0);
    const timer = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    const pollInterval = setInterval(async () => {
      try {
        const job = await getJobStatus(jobId);
        setCurrentJob(job);

        if (job.status === "READY" || job.status === "COMPLETED" || job.status === "SEMANTIC_READY") {
          clearInterval(pollInterval);
          clearInterval(timer);
          activateAndSyncWorkspace(job.workspace_id ? { workspace_id: job.workspace_id, ...initialData } : initialData);
          invalidateCache();
          await api.get("/workspaces").catch(() => {});
          await api.get("/workspace/active").catch(() => {});
          setLoading(false);
          setSuccess(true);
          setTimeout(() => {
            window.location.href = "/dynamic-dashboard";
          }, 1000);
        } else if (job.status === "FAILED") {
          clearInterval(pollInterval);
          clearInterval(timer);
          setLoading(false);
          const errDetail = job.error?.suggested_fix
            ? `${job.error.message || "Ingestion failed."} (${job.error.suggested_fix})`
            : job.error?.message || "Ingestion pipeline failed.";
          setErrorMsg(errDetail);
        } else if (job.status === "CANCELLED") {
          clearInterval(pollInterval);
          clearInterval(timer);
          setLoading(false);
          setErrorMsg("Ingestion was cancelled.");
        }
      } catch (err: any) {
        console.warn("[UploadCard] Polling job status warning:", err);
      }
    }, 800);
  }

  async function handleCancelJob() {
    if (!currentJob?.job_id) return;
    try {
      await cancelJob(currentJob.job_id);
      setErrorMsg("Dataset ingestion was cancelled.");
      setLoading(false);
      setCurrentJob(null);
    } catch (err) {
      console.error(err);
    }
  }

  async function processFiles(fileList: File[]) {
    try {
      setLoading(true);
      setSuccess(false);
      setErrorMsg("");
      setUploadProgress(0);
      setCurrentJob(null);

      let resultData: any = null;
      if (fileList.length === 1) {
        resultData = await uploadDataset(fileList[0], undefined, (pct) => {
          setUploadProgress(pct);
        });
        setProcessedCount(1);
      } else {
        resultData = await uploadMultipleDatasets(fileList, undefined, (pct) => {
          setUploadProgress(pct);
        });
        setProcessedCount(resultData.processed_datasets?.length || fileList.length);
      }

      setUploadProgress(100);

      if (resultData?.job_id) {
        await startJobPolling(resultData.job_id, resultData);
      } else {
        activateAndSyncWorkspace(resultData);
        invalidateCache();
        await api.get("/workspaces").catch(() => {});
        await api.get("/workspace/active").catch(() => {});
        setSuccess(true);
        setTimeout(() => {
          window.location.href = "/dynamic-dashboard";
        }, 800);
        setLoading(false);
      }
    } catch (error: any) {
      console.error(error);
      setLoading(false);
      if (error.response?.status === 401) {
        setErrorMsg("Session expired or authentication required. Please log in again.");
      } else {
        setErrorMsg(error.response?.data?.detail || "Failed to process dataset files. Please check file formats.");
      }
    }
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    await processFiles(Array.from(files));
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

    await processFiles(validFiles);
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
          disabled={loading}
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
          disabled={loading}
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
          onClick={() => !loading && inputRef.current?.click()}
          animate={{
            scale: isDragging ? 1.015 : 1,
            borderColor: isDragging ? "var(--primary-500)" : undefined,
            backgroundColor: isDragging ? "rgba(99,102,241,0.06)" : undefined,
          }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className={`border-2 border-dashed border-border-color rounded-2xl p-12 text-center transition-all duration-200 group flex flex-col items-center justify-center space-y-3 ${
            loading ? "opacity-60 cursor-not-allowed" : "cursor-pointer"
          } ${
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
              Click to select any files from your device folders. Memory-safe streaming pipeline up to 2GB per file.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-text-muted bg-surface-muted px-3 py-1.5 rounded-lg border border-border-color">
            <FileSpreadsheet className="w-3.5 h-3.5 text-primary-500" />
            <span>High-Performance Asynchronous Ingestion & Analysis</span>
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
            disabled={loading}
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
              disabled={loading}
              className="flex-1 px-4 py-2.5 bg-surface-muted border border-border-color rounded-xl text-xs text-text-primary outline-none focus:border-primary-500 font-mono"
            />
            <button
              onClick={() => handleImportLocalPath()}
              disabled={loading}
              className="px-5 py-2.5 bg-primary-600 hover:bg-primary-700 text-white text-xs font-semibold rounded-xl transition-all shadow-md shadow-primary-600/30 flex items-center gap-2 disabled:opacity-50"
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
                  disabled={loading}
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
                      if (loading) return;
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

      {/* Dynamic Status Feedback & Progress Panel */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="p-5 bg-surface rounded-2xl border border-border-color shadow-sm space-y-4"
          >
            {/* Header: Title & Elapsed Timer */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <motion.div
                  className="w-5 h-5 border-2 border-primary-600 border-t-transparent rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 0.9, ease: "linear" }}
                />
                <div>
                  <h4 className="text-xs font-bold text-text-primary">
                    {uploadProgress !== null && uploadProgress < 100
                      ? "Streaming Dataset to Server..."
                      : currentJob?.current_stage || "Processing Dataset Pipeline..."}
                  </h4>
                  <p className="text-[11px] text-text-muted mt-0.5">
                    {uploadProgress !== null && uploadProgress < 100
                      ? `Streaming chunks memory-safely (${uploadProgress}% uploaded)`
                      : currentJob?.message || "Running schema profiling, DuckDB parquet conversion, and semantic modeling."}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 text-xs font-mono text-text-secondary bg-surface-muted px-2.5 py-1 rounded-lg border border-border-color">
                  <Clock className="w-3.5 h-3.5 text-primary-500" />
                  <span>{elapsedSeconds}s</span>
                </div>
                {currentJob && (
                  <button
                    onClick={handleCancelJob}
                    className="px-2.5 py-1 bg-surface hover:bg-error-50 text-error-600 hover:text-error-700 rounded-lg text-xs font-semibold border border-border-color hover:border-error-200 transition-colors flex items-center gap-1"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Cancel</span>
                  </button>
                )}
              </div>
            </div>

            {/* Progress Bar */}
            <div className="space-y-1.5">
              <div className="w-full bg-surface-muted rounded-full h-2.5 overflow-hidden border border-border-color">
                <motion.div
                  className="bg-primary-600 h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${
                      uploadProgress !== null && uploadProgress < 100
                        ? uploadProgress
                        : currentJob?.progress_pct || 30
                    }%`,
                  }}
                />
              </div>
              <div className="flex justify-between text-[10px] font-mono text-text-muted">
                <span>Memory-safe stream</span>
                <span>
                  {uploadProgress !== null && uploadProgress < 100
                    ? `${uploadProgress}% network upload`
                    : `${currentJob?.progress_pct || 30}% pipeline completed`}
                </span>
              </div>
            </div>

            {/* Stage Steps List */}
            {currentJob?.steps && currentJob.steps.length > 0 && (
              <div className="pt-2 border-t border-border-light grid grid-cols-1 sm:grid-cols-2 gap-2">
                {currentJob.steps.map((st, i) => (
                  <div key={i} className="flex items-center gap-2 text-[11px]">
                    {st.status === "COMPLETED" ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-success-500 flex-shrink-0" />
                    ) : st.status === "PROCESSING" ? (
                      <RefreshCw className="w-3.5 h-3.5 text-primary-500 animate-spin flex-shrink-0" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-border-strong flex-shrink-0" />
                    )}
                    <span
                      className={
                        st.status === "COMPLETED"
                          ? "text-text-muted line-through"
                          : st.status === "PROCESSING"
                          ? "text-primary-600 font-bold"
                          : "text-text-secondary"
                      }
                    >
                      {st.step}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {success && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="p-5 bg-success-50 text-success-900 rounded-2xl border border-success-200 text-xs space-y-2"
          >
            <div className="flex items-center gap-2 font-bold text-success-800">
              <CheckCircle2 className="w-4 h-4 text-success-600" />
              <span>
                {processedCount} dataset(s) ingested & profiled successfully!
              </span>
            </div>
            {currentJob?.metrics && (
              <div className="text-[11px] font-mono text-success-700 flex flex-wrap gap-4 pt-1">
                {currentJob.metrics.rows !== undefined && (
                  <span>Rows: <strong>{currentJob.metrics.rows.toLocaleString()}</strong></span>
                )}
                {currentJob.metrics.columns !== undefined && (
                  <span>Cols: <strong>{currentJob.metrics.columns}</strong></span>
                )}
                {currentJob.metrics.domain && (
                  <span>Domain: <strong>{currentJob.metrics.domain}</strong></span>
                )}
                {currentJob.metrics.health_score !== undefined && (
                  <span>Health: <strong>{currentJob.metrics.health_score}/100</strong></span>
                )}
              </div>
            )}
            <p className="text-[11px] text-success-700">
              Launching intelligent dashboard view...
            </p>
          </motion.div>
        )}

        {errorMsg && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="p-4 bg-error-50 text-error-800 rounded-2xl border border-error-200 text-xs flex items-start gap-3"
          >
            <AlertCircle className="w-4 h-4 text-error-600 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-bold block">Ingestion Notice</span>
              <span className="leading-relaxed">{errorMsg}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
