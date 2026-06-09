"use client";

import { useMemo } from "react";
import { Images } from "lucide-react";
import type { SampleImage } from "@lora-training-studio/shared";
import { EmptyState } from "@/components/ui/empty-state";
import { RunAssetImage } from "@/components/runs/run-asset-image";

interface SampleGalleryProps {
  runId: string;
  samples: SampleImage[];
}

interface SampleGroup {
  label: string;
  order: number;
  items: SampleImage[];
}

export function SampleGallery({ runId, samples }: SampleGalleryProps) {
  // Group by step so the gallery reads as "what the model produced at each
  // checkpoint", with the final set last.
  const groups = useMemo<SampleGroup[]>(() => {
    const byStep = new Map<string, SampleGroup>();
    for (const s of samples) {
      const key = s.step === null ? "final" : String(s.step);
      const label = s.step === null ? "Final" : `Step ${s.step}`;
      const order = s.step === null ? Number.MAX_SAFE_INTEGER : s.step;
      if (!byStep.has(key)) byStep.set(key, { label, order, items: [] });
      byStep.get(key)!.items.push(s);
    }
    return [...byStep.values()].sort((a, b) => a.order - b.order);
  }, [samples]);

  if (samples.length === 0) {
    return (
      <EmptyState
        icon={Images}
        title="No samples yet"
        description="Sample images render as each checkpoint completes."
      />
    );
  }

  return (
    <div className="space-y-5">
      {groups.map((group) => (
        <div key={group.label}>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {group.label}
          </h4>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {group.items.map((s) => (
              <div
                key={s.key}
                className="aspect-square overflow-hidden rounded-md border border-border"
              >
                <RunAssetImage
                  runId={runId}
                  assetKey={s.key}
                  alt={`${group.label} sample ${s.index}`}
                  className="h-full w-full object-cover"
                />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
