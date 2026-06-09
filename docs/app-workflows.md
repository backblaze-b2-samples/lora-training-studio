<!-- last_verified: 2026-06-05 -->
# App Workflows

User journeys inside LoRA Training Studio.

## Train a LoRA (the main flow)

- User navigates to `/train`, names the run, picks an instance token (e.g. `sks dog`), a base model (label only), and training config (steps / rank / learning rate)
- Submitting `POST /runs` creates a manifest on B2 and redirects to `/library/{run_id}`
- On the run detail page, the **pipeline stepper** shows where the run is: dataset → captions → training → samples → download
- **Dataset tab**: drag training images in; each is uploaded to `lora-training/{run_id}/dataset/`, dimensions extracted, thumbnails shown via presigned URLs; remove any image before training
- **Captions tab**: edit each caption by hand, or click **Auto-caption all** (offline templated captions by default; Claude vision when `ANTHROPIC_API_KEY` is set). Captions are saved to `captions/{image_id}.txt`
- **Start training**: the run flips to `training` and a background job drives the trainer; the **Training tab** shows step progress and a live loss curve as checkpoints and sample images stream to B2 (polled while in flight)
- **Samples tab**: the sample gallery fills in per checkpoint step, then with a final set
- On completion, a **Download** card offers the trained `.safetensors` via a presigned attachment URL
- See: [LoRA Pipeline](features/lora-pipeline.md), [Training](features/training.md), [Captioning](features/captioning.md)

## Browse the LoRA Library

- User navigates to `/library`
- Every run under the `lora-training/` prefix is listed as a card (name, status badge, image count, instance token, created date)
- Open a card to reach the run detail page; delete a run to remove its entire prefix from B2
- See: [LoRA Library](features/lora-library.md)

## View the Dashboard

- User navigates to `/` (home)
- Stats cards show: total runs, LoRAs produced, training images, and total B2 storage used
- A storage-breakdown chart shows B2 bytes by artifact type (dataset, captions, checkpoints, LoRA, samples)
- A recent-runs table lists the latest runs with status
- See: [Dashboard](features/dashboard.md)

## Browse the full bucket (reusable base)

- User navigates to `/files`
- The full-bucket explorer lists every object (including run artifacts) in tree view with preview / download / delete
- Distinct from the Library: this is the generic browse-everything surface kept from the starter kit
- See: [File Browser](features/file-browser.md)

## Upload arbitrary files (reusable base)

- User navigates to `/upload`, drops or selects files; per-file progress; success/error toasts
- A generic B2 upload surface — separate from per-run dataset upload
- See: [File Upload](features/file-upload.md)
