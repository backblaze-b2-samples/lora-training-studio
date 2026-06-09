"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  autoCaption,
  createRun,
  deleteDatasetImage,
  deleteFile,
  deleteRun,
  getCaptions,
  getFiles,
  getFileStats,
  getPreviewUrl,
  getRun,
  getRunAssetUrl,
  getRunProgress,
  getRuns,
  getRunsStats,
  getUploadActivity,
  setCaption,
  startTraining,
  uploadDatasetImage,
} from "@/lib/api-client";
import type { FileMetadata } from "@lora-training-studio/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  // Run pipeline keys. `runs` is the root for invalidation after mutations.
  runs: ["runs"] as const,
  runsList: () => [...qk.runs, "list"] as const,
  runsStats: () => [...qk.runs, "stats"] as const,
  run: (runId: string) => [...qk.runs, "detail", runId] as const,
  runProgress: (runId: string) => [...qk.runs, "progress", runId] as const,
  captions: (runId: string) => [...qk.runs, "captions", runId] as const,
  runAsset: (runId: string, key: string) =>
    [...qk.runs, "asset", runId, key] as const,
};

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- LoRA Training Studio: run pipeline hooks ---

export function useRuns() {
  return useQuery({ queryKey: qk.runsList(), queryFn: getRuns });
}

export function useRunsStats() {
  return useQuery({ queryKey: qk.runsStats(), queryFn: getRunsStats });
}

export function useRun(runId: string) {
  return useQuery({
    queryKey: qk.run(runId),
    queryFn: () => getRun(runId),
    enabled: !!runId,
  });
}

// Poll progress while a run is training; stop once it settles. The component
// passes the current status so we don't poll completed/failed runs forever.
export function useRunProgress(runId: string, status: string | undefined) {
  return useQuery({
    queryKey: qk.runProgress(runId),
    queryFn: () => getRunProgress(runId),
    enabled: !!runId,
    refetchInterval: status === "training" || status === "sampling" ? 1500 : false,
  });
}

export function useCreateRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createRun,
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.runs }),
  });
}

export function useDeleteRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => deleteRun(runId),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.runs }),
  });
}

export function useUploadDatasetImage(runId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadDatasetImage(runId, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.run(runId) }),
  });
}

export function useDeleteDatasetImage(runId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (imageId: string) => deleteDatasetImage(runId, imageId),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.run(runId) }),
  });
}

export function useCaptions(runId: string) {
  return useQuery({
    queryKey: qk.captions(runId),
    queryFn: () => getCaptions(runId),
    enabled: !!runId,
  });
}

export function useSetCaption(runId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ imageId, text }: { imageId: string; text: string }) =>
      setCaption(runId, imageId, text),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.captions(runId) });
      qc.invalidateQueries({ queryKey: qk.run(runId) });
    },
  });
}

export function useAutoCaption(runId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => autoCaption(runId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.captions(runId) });
      qc.invalidateQueries({ queryKey: qk.run(runId) });
    },
  });
}

export function useStartTraining(runId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => startTraining(runId),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.run(runId) }),
  });
}

// Presigned asset URL (thumbnail / sample / LoRA). Short staleTime because
// the presigned URL itself expires and is cheap to regenerate.
export function useRunAssetUrl(runId: string, key: string | undefined) {
  return useQuery({
    queryKey: qk.runAsset(runId, key ?? ""),
    queryFn: () => getRunAssetUrl(runId, key as string),
    enabled: !!runId && !!key,
    staleTime: 5 * 60_000,
  });
}
