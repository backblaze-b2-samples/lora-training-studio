"use client";

import { useState } from "react";
import { Sparkles, Loader2 } from "lucide-react";
import { toast } from "sonner";
import type { Caption, DatasetImage, RunStatus } from "@lora-training-studio/shared";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/components/ui/empty-state";
import { ImageIcon } from "lucide-react";
import { useAutoCaption, useSetCaption } from "@/lib/queries";
import { RunAssetImage } from "@/components/runs/run-asset-image";

interface CaptionEditorProps {
  runId: string;
  images: DatasetImage[];
  captions: Caption[];
  status: RunStatus;
}

function CaptionRow({
  runId,
  image,
  initial,
  locked,
}: {
  runId: string;
  image: DatasetImage;
  initial: string;
  locked: boolean;
}) {
  const [text, setText] = useState(initial);
  const [lastInitial, setLastInitial] = useState(initial);
  const setCaption = useSetCaption(runId);

  // When auto-caption rewrites the server value, adopt it during render
  // (the recommended pattern over a setState-in-effect).
  if (initial !== lastInitial) {
    setLastInitial(initial);
    setText(initial);
  }

  const dirty = text !== initial;

  return (
    <div className="flex gap-3 rounded-md border border-border p-3">
      <div className="h-20 w-20 shrink-0 overflow-hidden rounded-md border border-border">
        <RunAssetImage
          runId={runId}
          assetKey={image.key}
          alt={image.filename}
          className="h-full w-full object-cover"
        />
      </div>
      <div className="flex-1 space-y-2">
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={2}
          placeholder="Describe this image…"
          disabled={locked}
          className="resize-none text-sm"
        />
        <div className="flex justify-end">
          <Button
            size="sm"
            variant="outline"
            disabled={!dirty || locked || setCaption.isPending}
            onClick={() =>
              setCaption.mutate(
                { imageId: image.image_id, text },
                { onSuccess: () => toast.success("Caption saved") },
              )
            }
          >
            {setCaption.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              "Save"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function CaptionEditor({ runId, images, captions, status }: CaptionEditorProps) {
  const autoCaption = useAutoCaption(runId);
  const locked = status === "training" || status === "sampling";
  const byImage = new Map(captions.map((c) => [c.image_id, c.text]));

  if (images.length === 0) {
    return (
      <EmptyState
        icon={ImageIcon}
        title="No images to caption"
        description="Add dataset images first, then caption them here."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button
          size="sm"
          disabled={locked || autoCaption.isPending}
          onClick={() =>
            autoCaption.mutate(undefined, {
              onSuccess: (res) => toast.success(`Auto-captioned ${res.length} images`),
              onError: (err) => toast.error(`Auto-caption failed: ${err.message}`),
            })
          }
        >
          {autoCaption.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Sparkles className="h-3.5 w-3.5" />
          )}
          Auto-caption all
        </Button>
      </div>
      <div className="space-y-3">
        {images.map((img) => (
          <CaptionRow
            key={img.image_id}
            runId={runId}
            image={img}
            initial={byImage.get(img.image_id) ?? ""}
            locked={locked}
          />
        ))}
      </div>
    </div>
  );
}
