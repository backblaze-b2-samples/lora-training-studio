"use client";

import { Check } from "lucide-react";
import type { StageState } from "@lora-training-studio/shared";

const STAGE_LABELS: Record<string, string> = {
  dataset: "Dataset",
  captions: "Captions",
  training: "Training",
  samples: "Samples",
  download: "Download",
};

export function PipelineStepper({ stages }: { stages: StageState[] }) {
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-3">
      {stages.map((stage, i) => {
        const done = stage.status === "done";
        const active = stage.status === "active";
        return (
          <li key={stage.name} className="flex items-center gap-2">
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-full border text-xs font-semibold ${
                done
                  ? "border-primary bg-primary text-primary-foreground"
                  : active
                    ? "border-primary text-primary"
                    : "border-border text-muted-foreground"
              }`}
            >
              {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
            </div>
            <span
              className={`text-sm ${
                active || done ? "font-medium text-foreground" : "text-muted-foreground"
              }`}
            >
              {STAGE_LABELS[stage.name] ?? stage.name}
            </span>
            {i < stages.length - 1 && (
              <span className="mx-1 h-px w-6 bg-border" aria-hidden />
            )}
          </li>
        );
      })}
    </ol>
  );
}
