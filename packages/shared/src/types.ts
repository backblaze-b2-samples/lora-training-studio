export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- LoRA Training Studio: run pipeline types ---
// These mirror the Pydantic models in services/api/app/types/runs.py.

export type RunStatus =
  | "created"
  | "captioning"
  | "ready_to_train"
  | "training"
  | "sampling"
  | "complete"
  | "failed";

export type StageName =
  | "dataset"
  | "captions"
  | "training"
  | "samples"
  | "download";

export type StageStatus = "pending" | "active" | "done";

export interface RunConfig {
  base_model: string;
  instance_token: string;
  steps: number;
  rank: number;
  learning_rate: number;
}

export interface StageState {
  name: StageName;
  status: StageStatus;
}

export interface DatasetImage {
  image_id: string;
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  width: number | null;
  height: number | null;
}

export interface Caption {
  image_id: string;
  text: string;
  key: string;
}

export interface SampleImage {
  key: string;
  step: number | null;
  index: number;
}

export interface LossPoint {
  step: number;
  loss: number;
}

export interface TrainingProgress {
  status: RunStatus;
  current_step: number;
  total_steps: number;
  loss_curve: LossPoint[];
  latest_checkpoint_key: string | null;
  message: string | null;
}

export interface StorageBreakdownItem {
  category: string;
  object_count: number;
  size_bytes: number;
  size_human: string;
}

export interface StorageBreakdown {
  items: StorageBreakdownItem[];
  total_size_bytes: number;
  total_size_human: string;
}

export interface RunSummary {
  run_id: string;
  name: string;
  status: RunStatus;
  config: RunConfig;
  image_count: number;
  created_at: string;
  updated_at: string;
  lora_key: string | null;
}

export interface RunDetail {
  run_id: string;
  name: string;
  status: RunStatus;
  config: RunConfig;
  stages: StageState[];
  dataset: DatasetImage[];
  captions: Caption[];
  progress: TrainingProgress;
  samples: SampleImage[];
  lora_key: string | null;
  created_at: string;
  updated_at: string;
}

export interface RunsStats {
  total_runs: number;
  completed_runs: number;
  loras_produced: number;
  training_images: number;
  storage: StorageBreakdown;
}

export interface CreateRunRequest {
  name: string;
  config: RunConfig;
}
