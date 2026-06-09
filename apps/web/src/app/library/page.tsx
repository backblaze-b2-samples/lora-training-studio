import Link from "next/link";
import { Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { RunGrid } from "@/components/runs/run-grid";

export default function LibraryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">LoRA Library</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Every run, scoped to the <code className="font-mono">lora-training/</code>{" "}
            prefix in your B2 bucket. Open one to view its artifacts and download
            the LoRA.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/train">
            <Wand2 className="h-3.5 w-3.5" />
            New run
          </Link>
        </Button>
      </div>
      <RunGrid />
    </div>
  );
}
