import type { RunStatus } from "@lora-training-studio/shared";
import { Badge } from "@/components/ui/badge";

const LABELS: Record<RunStatus, string> = {
  created: "Created",
  captioning: "Captioning",
  ready_to_train: "Ready to train",
  training: "Training",
  sampling: "Sampling",
  complete: "Complete",
  failed: "Failed",
};

// Map each status to a Badge variant. "training"/"sampling" use the default
// (accent) to read as in-flight; terminal states use secondary/destructive.
const VARIANTS: Record<RunStatus, "default" | "secondary" | "destructive" | "outline"> = {
  created: "outline",
  captioning: "outline",
  ready_to_train: "secondary",
  training: "default",
  sampling: "default",
  complete: "secondary",
  failed: "destructive",
};

export function RunStatusBadge({ status }: { status: RunStatus }) {
  return (
    <Badge variant={VARIANTS[status]} className="capitalize">
      {LABELS[status]}
    </Badge>
  );
}
