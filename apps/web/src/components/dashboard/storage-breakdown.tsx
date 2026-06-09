"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Database } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useRunsStats } from "@/lib/queries";

const chartConfig = {
  size_mb: {
    label: "Size (MB)",
    color: "var(--chart-1)",
  },
} satisfies ChartConfig;

const CATEGORY_LABELS: Record<string, string> = {
  dataset: "Dataset",
  captions: "Captions",
  checkpoints: "Checkpoints",
  lora: "LoRA",
  samples: "Samples",
  manifest: "Manifest",
};

export function StorageBreakdown() {
  const { data: stats, error, refetch } = useRunsStats();

  // The "heavy across the lifecycle" story: B2 bytes by artifact type.
  const data = useMemo(
    () =>
      (stats?.storage.items ?? []).map((item) => ({
        category: CATEGORY_LABELS[item.category] ?? item.category,
        size_mb: Number((item.size_bytes / (1024 * 1024)).toFixed(2)),
      })),
    [stats],
  );

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">B2 Storage by Artifact</CardTitle>
        <CardDescription className="text-xs">
          Where the {stats?.storage.total_size_human ?? "0 B"} in your bucket lives
        </CardDescription>
      </CardHeader>
      <CardContent className="p-5">
        {error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={Database}
            title="No artifacts yet"
            description="Create a run and train it to see storage fill in by type."
          />
        ) : (
          <ChartContainer config={chartConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="storage-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-size_mb)" stopOpacity={0.95} />
                  <stop offset="100%" stopColor="var(--color-size_mb)" stopOpacity={0.55} />
                </linearGradient>
              </defs>
              <CartesianGrid
                vertical={false}
                strokeDasharray="3 3"
                stroke="var(--border)"
              />
              <XAxis
                dataKey="category"
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
                width={36}
              />
              <ChartTooltip
                cursor={{ fill: "var(--accent-subtle)" }}
                content={<ChartTooltipContent />}
              />
              <Bar
                dataKey="size_mb"
                fill="url(#storage-fill)"
                radius={[4, 4, 0, 0]}
                animationDuration={500}
                animationEasing="ease-out"
              />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
