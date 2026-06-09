"use client";

import { ImageOff } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useRunAssetUrl } from "@/lib/queries";

interface RunAssetImageProps {
  runId: string;
  assetKey: string;
  alt: string;
  className?: string;
}

// Presigned, inline-disposition image. Resolving the URL is a query so it's
// cached and deduped — multiple thumbnails of the same key share one fetch.
export function RunAssetImage({ runId, assetKey, alt, className }: RunAssetImageProps) {
  const { data, isLoading, error } = useRunAssetUrl(runId, assetKey);

  if (isLoading) {
    return <Skeleton className={className ?? "h-full w-full"} />;
  }
  if (error || !data) {
    return (
      <div className={`flex items-center justify-center bg-muted ${className ?? ""}`}>
        <ImageOff className="h-5 w-5 text-muted-foreground" />
      </div>
    );
  }
  // Presigned B2 URL — short-lived and not known at build time, so next/image
  // adds no value here.
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={data.url} alt={alt} className={className} loading="lazy" />
  );
}
