"use client";

import { useState, useRef, useCallback } from "react";
import api from "./api";
import { ProgressStageItem } from "@/components/ui/RealtimeProgressModal";

export interface ProgressModalConfig {
  title: string;
  subtitle?: string;
  stages: string[];
  doneButtonText?: string;
  onDone?: () => void;
  canCancel?: boolean;
}

export function useProgressModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [percentage, setPercentage] = useState(0);
  const [currentStage, setCurrentStage] = useState("");
  const [stages, setStages] = useState<ProgressStageItem[]>([]);
  const [status, setStatus] = useState<"processing" | "completed" | "failed">("processing");
  const [errorMessage, setErrorMessage] = useState<string | undefined>(undefined);
  const [stats, setStats] = useState<any>(undefined);
  const [doneButtonText, setDoneButtonText] = useState("View Results");

  const pollIntervalRef = useRef<any>(null);
  const onDoneCallbackRef = useRef<(() => void) | undefined>(undefined);

  const startProgress = useCallback((config: ProgressModalConfig) => {
    setTitle(config.title);
    setSubtitle(config.subtitle || "");
    setDoneButtonText(config.doneButtonText || "View Results");
    onDoneCallbackRef.current = config.onDone;
    setPercentage(5);
    setStatus("processing");
    setErrorMessage(undefined);
    setStats(undefined);

    const initialStages: ProgressStageItem[] = config.stages.map((name, idx) => ({
      name,
      status: idx === 0 ? "in_progress" : "pending",
    }));
    setStages(initialStages);
    setCurrentStage(config.stages[0] || "Initializing...");
    setIsOpen(true);
  }, []);

  const setProgressStage = useCallback((stageIndex: number, pct: number, message?: string) => {
    setPercentage(pct);
    setStages((prev) =>
      prev.map((s, idx) => {
        if (idx < stageIndex) return { ...s, status: "completed" };
        if (idx === stageIndex) return { ...s, status: "in_progress", detail: message };
        return { ...s, status: "pending" };
      })
    );
    if (message) setCurrentStage(message);
  }, []);

  const completeProgress = useCallback((completionStats?: any, message = "Operation completed successfully") => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    setPercentage(100);
    setStatus("completed");
    setCurrentStage(message);
    setStats(completionStats);
    setStages((prev) => prev.map((s) => ({ ...s, status: "completed" })));
  }, []);

  const failProgress = useCallback((error: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    setStatus("failed");
    setErrorMessage(error);
    setCurrentStage("Failed");
    setStages((prev) =>
      prev.map((s) => (s.status === "in_progress" ? { ...s, status: "failed" } : s))
    );
  }, []);

  const trackWorkspaceStatus = useCallback(
    (workspaceId: string, onComplete?: (data: any) => void) => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

      pollIntervalRef.current = setInterval(async () => {
        try {
          const res = await api.get(`/workspace/${workspaceId}/status`);
          const stData = res.data;
          if (!stData) return;

          if (stData.progress !== undefined) {
            setPercentage(stData.progress);
          }
          if (stData.current_step || stData.message) {
            setCurrentStage(stData.current_step || stData.message);
          }

          if (stData.steps && Array.isArray(stData.steps)) {
            setStages(
              stData.steps.map((st: any) => ({
                name: st.step || st.name,
                status:
                  st.status === "COMPLETED"
                    ? "completed"
                    : st.status === "FAILED"
                    ? "failed"
                    : st.status === "IN_PROGRESS"
                    ? "in_progress"
                    : "pending",
              }))
            );
          }

          if (stData.status === "COMPLETED" || stData.status === "READY" || stData.status === "SEMANTIC_READY" || stData.is_ready) {
            clearInterval(pollIntervalRef.current);
            completeProgress(stData.metrics, "Workspace intelligence ready!");
            if (onComplete) onComplete(stData);
          } else if (stData.status === "FAILED") {
            clearInterval(pollIntervalRef.current);
            failProgress(stData.error?.message || stData.message || "Pipeline processing failed.");
          }
        } catch (err: any) {
          console.debug("[useProgressModal] Polling status warning:", err);
        }
      }, 900);
    },
    [completeProgress, failProgress]
  );

  const closeModal = useCallback(() => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    setIsOpen(false);
  }, []);

  const handleDone = useCallback(() => {
    closeModal();
    if (onDoneCallbackRef.current) {
      onDoneCallbackRef.current();
    }
  }, [closeModal]);

  return {
    isOpen,
    title,
    subtitle,
    percentage,
    currentStage,
    stages,
    status,
    errorMessage,
    stats,
    doneButtonText,
    startProgress,
    setProgressStage,
    completeProgress,
    failProgress,
    trackWorkspaceStatus,
    closeModal,
    handleDone,
  };
}
