"use client";

import { Play, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RunStatusBadge } from "@/components/runs/run-status-badge";
import { PipelineStepper } from "@/components/runs/pipeline-stepper";
import { DatasetGrid } from "@/components/runs/dataset-grid";
import { CaptionEditor } from "@/components/runs/caption-editor";
import { TrainingMonitor } from "@/components/runs/training-monitor";
import { SampleGallery } from "@/components/runs/sample-gallery";
import { LoraDownloadCard } from "@/components/runs/lora-download-card";
import { useRun, useRunProgress, useStartTraining } from "@/lib/queries";

export function RunDetail({ runId }: { runId: string }) {
  const { data: run, isLoading, error, refetch } = useRun(runId);
  // Poll progress while the run is in flight; merge it over the manifest copy.
  const { data: livePolled } = useRunProgress(runId, run?.status);
  const startTraining = useStartTraining(runId);

  if (isLoading) {
    return <Skeleton className="h-96 w-full" />;
  }
  if (error || !run) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const progress = livePolled ?? run.progress;
  const canTrain =
    run.captions.length > 0 &&
    run.status !== "training" &&
    run.status !== "sampling";

  return (
    <div className="space-y-6">
      <div className="animate-fade-in border-b border-border pb-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="page-title">{run.name}</h1>
              <RunStatusBadge status={run.status} />
            </div>
            <p className="mt-1.5 font-mono text-xs text-muted-foreground">
              token {run.config.instance_token} · {run.config.steps} steps · rank{" "}
              {run.config.rank} · lr {run.config.learning_rate}
            </p>
          </div>
          <Button
            size="sm"
            disabled={!canTrain || startTraining.isPending}
            onClick={() =>
              startTraining.mutate(undefined, {
                onSuccess: () => toast.success("Training started"),
                onError: (err) => toast.error(`Could not start: ${err.message}`),
              })
            }
          >
            {startTraining.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            Start training
          </Button>
        </div>
        <div className="mt-4">
          <PipelineStepper stages={run.stages} />
        </div>
      </div>

      {run.lora_key && <LoraDownloadCard runId={runId} loraKey={run.lora_key} />}

      <Tabs defaultValue="dataset">
        <TabsList>
          <TabsTrigger value="dataset">Dataset ({run.dataset.length})</TabsTrigger>
          <TabsTrigger value="captions">Captions</TabsTrigger>
          <TabsTrigger value="training">Training</TabsTrigger>
          <TabsTrigger value="samples">Samples ({run.samples.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="dataset">
          <Card>
            <CardHeader className="border-b border-border py-4 px-5">
              <CardTitle className="card-title">Training images</CardTitle>
            </CardHeader>
            <CardContent className="p-5">
              <DatasetGrid runId={runId} images={run.dataset} status={run.status} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="captions">
          <Card>
            <CardHeader className="border-b border-border py-4 px-5">
              <CardTitle className="card-title">Captions</CardTitle>
            </CardHeader>
            <CardContent className="p-5">
              <CaptionEditor
                runId={runId}
                images={run.dataset}
                captions={run.captions}
                status={run.status}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="training">
          <Card>
            <CardHeader className="border-b border-border py-4 px-5">
              <CardTitle className="card-title">Training monitor</CardTitle>
            </CardHeader>
            <CardContent className="p-5">
              <TrainingMonitor progress={progress} status={run.status} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="samples">
          <Card>
            <CardHeader className="border-b border-border py-4 px-5">
              <CardTitle className="card-title">Sample gallery</CardTitle>
            </CardHeader>
            <CardContent className="p-5">
              <SampleGallery runId={runId} samples={run.samples} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
