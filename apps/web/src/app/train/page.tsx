"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Wand2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCreateRun } from "@/lib/queries";

const BASE_MODELS = [
  // SD 1.5 first: it's the model the default (local) trainer actually fine-tunes.
  { value: "sd-1.5", label: "Stable Diffusion 1.5" },
  { value: "sdxl-base-1.0", label: "SDXL Base 1.0" },
  { value: "flux.1-dev", label: "FLUX.1 [dev]" },
];

export default function TrainPage() {
  const router = useRouter();
  const createRun = useCreateRun();

  const [name, setName] = useState("");
  const [instanceToken, setInstanceToken] = useState("sks");
  const [baseModel, setBaseModel] = useState(BASE_MODELS[0].value);
  const [steps, setSteps] = useState(1000);
  const [rank, setRank] = useState(16);
  const [learningRate, setLearningRate] = useState(0.0001);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Give your run a name");
      return;
    }
    createRun.mutate(
      {
        name: name.trim(),
        config: {
          base_model: baseModel,
          instance_token: instanceToken.trim() || "sks",
          steps,
          rank,
          learning_rate: learningRate,
        },
      },
      {
        onSuccess: (run) => {
          toast.success("Run created");
          router.push(`/library/${run.run_id}`);
        },
        onError: (err) => toast.error(`Could not create run: ${err.message}`),
      },
    );
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">New run</h1>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Name the run and set its training config. You&apos;ll add images and
          captions on the next screen. Training runs a real on-device SD 1.5
          LoRA by default — set TRAINER_PROVIDER=simulated for a no-GPU demo.
        </p>
      </div>

      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Configuration</CardTitle>
        </CardHeader>
        <CardContent className="p-5">
          <form onSubmit={onSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="name">Run name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. my-corgi-lora"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="token">Instance token</Label>
              <Input
                id="token"
                value={instanceToken}
                onChange={(e) => setInstanceToken(e.target.value)}
                placeholder="sks dog"
              />
              <p className="text-xs text-muted-foreground">
                The rare token your subject is bound to (e.g. &quot;sks dog&quot;).
              </p>
            </div>

            <div className="space-y-2">
              <Label>Base model</Label>
              <Select value={baseModel} onValueChange={setBaseModel}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {BASE_MODELS.map((m) => (
                    <SelectItem key={m.value} value={m.value}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="steps">Steps</Label>
                <Input
                  id="steps"
                  type="number"
                  min={10}
                  max={10000}
                  value={steps}
                  onChange={(e) => setSteps(Number(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="rank">Rank</Label>
                <Input
                  id="rank"
                  type="number"
                  min={1}
                  max={256}
                  value={rank}
                  onChange={(e) => setRank(Number(e.target.value))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lr">Learning rate</Label>
                <Input
                  id="lr"
                  type="number"
                  step={0.00001}
                  min={0}
                  value={learningRate}
                  onChange={(e) => setLearningRate(Number(e.target.value))}
                />
              </div>
            </div>

            <div className="flex justify-end">
              <Button type="submit" disabled={createRun.isPending}>
                {createRun.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Wand2 className="h-4 w-4" />
                )}
                Create run
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
