<!-- last_verified: 2026-06-05 -->
# Security

Security principles and implementation for LoRA Training Studio.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/PUT/DELETE/OPTIONS` (PUT is used by the caption editor)
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4
- **Client -> B2**: Presigned URLs — attachment disposition for the LoRA download, inline disposition for dataset thumbnails and sample previews (10-min expiry)

## Upload Validation

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against allowlist
- Chunked streaming with size enforcement (100MB default)
- Content-type allowlist (images, PDFs, text, archives, audio/video)
- Empty file rejection

## File Key Validation

- Empty keys rejected
- Path traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- The full-bucket `/files` explorer treats the bucket as the access
  boundary — add prefix scoping in
  `services/api/app/service/files.py::validate_key` if your deployment
  shares a bucket with other workloads
- Per-run asset access (`GET /runs/{id}/asset`) validates that the requested
  key belongs to that run's `lora-training/{run_id}/` prefix, preventing
  cross-run reads via a guessed key

## Download Safety

- Presigned URLs force `Content-Disposition: attachment`
- Prevents inline rendering of user-uploaded content (XSS mitigation)

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values
- Optional `REPLICATE_API_TOKEN` / `ANTHROPIC_API_KEY` are read the same way; the default trainer and captioner need neither

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
