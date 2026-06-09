"use client";

import { useMemo } from "react";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import { Activity } from "lucide-react";
import type { RunStatus, TrainingProgress } from "@lora-training-studio/shared";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { Progress } from "@/components/ui/progress";
import { EmptyState } from "@/components/ui/empty-state";

const chartConfig = {
  loss: { label: "Loss", color: "var(--chart-1)" },
} satisfies ChartConfig;

interface TrainingMonitorProps {
  progress: TrainingProgress;
  status: RunStatus;
}

export function TrainingMonitor({ progress, status }: TrainingMonitorProps) {
  const data = useMemo(
    () => progress.loss_curve.map((p) => ({ step: p.step, loss: p.loss })),
    [progress.loss_curve],
  );

  const pct =
    progress.total_steps > 0
      ? Math.round((progress.current_step / progress.total_steps) * 100)
      : 0;

  if (status === "created" || status === "captioning" || status === "ready_to_train") {
    return (
      <EmptyState
        icon={Activity}
        title="Training hasn't started"
        description="Caption the dataset, then start training to watch the loss curve."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="mb-1.5 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {progress.message ?? "Training"}
          </span>
          <span className="font-medium tabular-nums">
            {progress.current_step} / {progress.total_steps} steps
          </span>
        </div>
        <Progress value={pct} />
      </div>

      {data.length > 0 && (
        <ChartContainer config={chartConfig} className="h-[220px] w-full">
          <LineChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
            <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="step"
              tickLine={false}
              axisLine={false}
              tickMargin={10}
              fontSize={11}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickMargin={6}
              fontSize={11}
              width={40}
              domain={[0, "auto"]}
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Line
              type="monotone"
              dataKey="loss"
              stroke="var(--color-loss)"
              strokeWidth={2}
              dot={false}
              animationDuration={400}
            />
          </LineChart>
        </ChartContainer>
      )}
    </div>
  );
}
