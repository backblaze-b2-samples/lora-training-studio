import type {
  Caption,
  CreateRunRequest,
  DailyUploadCount,
  DatasetImage,
  FileMetadata,
  FileUploadResponse,
  RunDetail,
  RunsStats,
  RunSummary,
  TrainingProgress,
  UploadStats,
} from "@lora-training-studio/shared";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Typed API error with HTTP status code for caller-side branching. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** True for 408, 429, 500, 502, 503, 504 — worth retrying. */
  get isRetryable(): boolean {
    return [408, 429, 500, 502, 503, 504].includes(this.status);
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    // Network failure (offline, DNS, CORS, etc.)
    throw new ApiError("Network error — check your connection", 0);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body.detail || `API error: ${res.status}`,
      res.status,
    );
  }
  return res.json();
}

export async function getHealth() {
  return apiFetch<{ status: string; b2_connected: boolean }>("/health");
}

export async function getFiles(prefix = "", limit = 100) {
  return apiFetch<FileMetadata[]>(
    `/files?prefix=${encodeURIComponent(prefix)}&limit=${limit}`
  );
}

export async function getFileStats() {
  return apiFetch<UploadStats>("/files/stats");
}

export async function getUploadActivity(days = 7) {
  return apiFetch<DailyUploadCount[]>(`/files/stats/activity?days=${days}`);
}

export async function getFile(key: string) {
  return apiFetch<FileMetadata>(`/files/${key}`);
}

export async function getDownloadUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/download`);
}

/** Preview-only presigned URL — does NOT increment the download counter. */
export async function getPreviewUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/preview`);
}

export async function deleteFile(key: string) {
  return apiFetch<{ deleted: boolean; key: string }>(`/files/${key}`, {
    method: "DELETE",
  });
}

export function uploadFile(
  file: File,
  onProgress?: (percent: number) => void
): Promise<FileUploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          reject(new ApiError(body.detail || `Upload failed: ${xhr.status}`, xhr.status));
        } catch {
          reject(new ApiError(`Upload failed: ${xhr.status}`, xhr.status));
        }
      }
    });

    xhr.addEventListener("error", () =>
      reject(new ApiError("Network error — check your connection", 0)),
    );
    xhr.addEventListener("abort", () =>
      reject(new ApiError("Upload aborted", 0)),
    );

    xhr.open("POST", `${API_BASE}/upload`);
    xhr.send(formData);
  });
}

// --- LoRA Training Studio: run pipeline ---

export async function getRuns() {
  return apiFetch<RunSummary[]>("/runs");
}

export async function getRunsStats() {
  return apiFetch<RunsStats>("/runs/stats");
}

export async function getRun(runId: string) {
  return apiFetch<RunDetail>(`/runs/${runId}`);
}

export async function getRunProgress(runId: string) {
  return apiFetch<TrainingProgress>(`/runs/${runId}/progress`);
}

export async function createRun(body: CreateRunRequest) {
  return apiFetch<RunDetail>("/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function deleteRun(runId: string) {
  return apiFetch<{ deleted: boolean; run_id: string; objects: number }>(
    `/runs/${runId}`,
    { method: "DELETE" },
  );
}

export function uploadDatasetImage(
  runId: string,
  file: File,
): Promise<DatasetImage> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<DatasetImage>(`/runs/${runId}/dataset`, {
    method: "POST",
    body: formData,
  });
}

export async function deleteDatasetImage(runId: string, imageId: string) {
  return apiFetch<{ deleted: boolean; image_id: string }>(
    `/runs/${runId}/dataset/${imageId}`,
    { method: "DELETE" },
  );
}

export async function getCaptions(runId: string) {
  return apiFetch<Caption[]>(`/runs/${runId}/captions`);
}

export async function setCaption(runId: string, imageId: string, text: string) {
  return apiFetch<Caption>(`/runs/${runId}/captions/${imageId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

export async function autoCaption(runId: string) {
  return apiFetch<Caption[]>(`/runs/${runId}/auto-caption`, { method: "POST" });
}

export async function startTraining(runId: string) {
  return apiFetch<{ run_id: string; status: string }>(`/runs/${runId}/train`, {
    method: "POST",
  });
}

/** Presigned URL for a per-run asset (thumbnail, sample, or LoRA download). */
export async function getRunAssetUrl(runId: string, key: string) {
  return apiFetch<{ url: string }>(
    `/runs/${runId}/asset?key=${encodeURIComponent(key)}`,
  );
}
