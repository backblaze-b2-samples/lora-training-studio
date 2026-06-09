"use client";

import Link from "next/link";
import { Wand2, ImageIcon, Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { RunStatusBadge } from "@/components/runs/run-status-badge";
import { useDeleteRun, useRuns } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

export function RunGrid() {
  const { data: runs = [], isLoading, error, refetch } = useRuns();
  const deleteRun = useDeleteRun();

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-36 w-full" />
        ))}
      </div>
    );
  }
  if (error) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }
  if (runs.length === 0) {
    return (
      <EmptyState
        icon={Wand2}
        title="No runs yet"
        description="Start your first run from the Train page."
      />
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {runs.map((run) => (
        <Card key={run.run_id} className="card-hover">
          <CardHeader className="flex flex-row items-start justify-between gap-2 px-4 pt-4 pb-2 space-y-0">
            <Link
              href={`/library/${run.run_id}`}
              className="min-w-0 flex-1 font-medium hover:underline"
            >
              <span className="block truncate">{run.name}</span>
            </Link>
            <RunStatusBadge status={run.status} />
          </CardHeader>
          <CardContent className="space-y-3 px-4 pb-4">
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <ImageIcon className="h-3.5 w-3.5" />
                {run.image_count} images
              </span>
              <span className="font-mono">{run.config.instance_token}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {formatDate(run.created_at)}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-muted-foreground hover:text-destructive"
                disabled={deleteRun.isPending}
                onClick={() =>
                  deleteRun.mutate(run.run_id, {
                    onSuccess: () => toast.success("Run deleted"),
                    onError: (err) => toast.error(`Delete failed: ${err.message}`),
                  })
                }
              >
                {deleteRun.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Trash2 className="h-3.5 w-3.5" />
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
