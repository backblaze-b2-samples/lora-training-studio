"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getRunAssetUrl } from "@/lib/api-client";

interface LoraDownloadCardProps {
  runId: string;
  loraKey: string;
}

export function LoraDownloadCard({ runId, loraKey }: LoraDownloadCardProps) {
  const [loading, setLoading] = useState(false);
  const filename = loraKey.split("/").pop() ?? "lora.safetensors";

  // Fetch a fresh presigned (attachment) URL on click, then navigate — keeps
  // the URL short-lived rather than baking it into the DOM.
  const onDownload = async () => {
    setLoading(true);
    try {
      const { url } = await getRunAssetUrl(runId, loraKey);
      window.location.href = url;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Download failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="border-primary/40 bg-accent-subtle">
      <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
        <div>
          <p className="text-sm font-medium">Trained LoRA ready</p>
          <p className="font-mono text-xs text-muted-foreground">{filename}</p>
        </div>
        <Button size="sm" onClick={onDownload} disabled={loading}>
          {loading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Download className="h-3.5 w-3.5" />
          )}
          Download .safetensors
        </Button>
      </CardContent>
    </Card>
  );
}
