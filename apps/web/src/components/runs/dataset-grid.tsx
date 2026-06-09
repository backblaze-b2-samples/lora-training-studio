"use client";

import { useCallback, useRef } from "react";
import { useDropzone } from "react-dropzone";
import { ImagePlus, X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import type { DatasetImage, RunStatus } from "@lora-training-studio/shared";
import { Button } from "@/components/ui/button";
import { useDeleteDatasetImage, useUploadDatasetImage } from "@/lib/queries";
import { RunAssetImage } from "@/components/runs/run-asset-image";

interface DatasetGridProps {
  runId: string;
  images: DatasetImage[];
  status: RunStatus;
}

const ACCEPT = {
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "image/webp": [".webp"],
};

export function DatasetGrid({ runId, images, status }: DatasetGridProps) {
  const upload = useUploadDatasetImage(runId);
  const remove = useDeleteDatasetImage(runId);
  const pending = useRef(0);
  const locked = status === "training" || status === "sampling";

  const onDrop = useCallback(
    (files: File[]) => {
      pending.current += files.length;
      files.forEach((file) =>
        upload.mutate(file, {
          onError: (err) => toast.error(`Upload failed: ${err.message}`),
          onSettled: () => {
            pending.current -= 1;
          },
        }),
      );
    },
    [upload],
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: ACCEPT,
    noClick: true,
    disabled: locked,
  });

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`rounded-lg border border-dashed p-6 text-center transition-colors ${
          isDragActive ? "border-primary bg-accent-subtle" : "border-border"
        } ${locked ? "opacity-60" : ""}`}
      >
        <input {...getInputProps()} />
        <ImagePlus className="mx-auto h-6 w-6 text-muted-foreground" />
        <p className="mt-2 text-sm text-muted-foreground">
          Drag training images here, or
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-2"
          onClick={open}
          disabled={locked}
        >
          Browse images
        </Button>
      </div>

      {images.length > 0 && (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5">
          {images.map((img) => (
            <div
              key={img.image_id}
              className="group relative aspect-square overflow-hidden rounded-md border border-border"
            >
              <RunAssetImage
                runId={runId}
                assetKey={img.key}
                alt={img.filename}
                className="h-full w-full object-cover"
              />
              {!locked && (
                <button
                  type="button"
                  aria-label={`Remove ${img.filename}`}
                  onClick={() => remove.mutate(img.image_id)}
                  className="absolute right-1 top-1 hidden rounded-full bg-background/90 p-1 text-foreground shadow-sm group-hover:block"
                >
                  {remove.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <X className="h-3.5 w-3.5" />
                  )}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
