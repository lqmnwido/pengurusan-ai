# Document Translation

Open WebUI exposes a document translation flow under:

`/api/v1/files/translation-jobs`

## Upload

`POST /api/v1/files/translation-jobs/upload`

Multipart form fields:

- `file`: PDF or DOCX
- `target_language`: default `Malay`
- `source_language`: default `auto`
- `model`: default `deepseekTranslateV4`
- `force_ocr`: default `false`
- `generate_output_file`: default `true`

The response includes a job object and, when translation completes, either:

- `translation_text`
- a generated file reference in `file`

## Poll status

`GET /api/v1/files/translation-jobs/{job_id}`

Returns the current job state and final output reference.

## History

`GET /api/v1/files/translation-jobs/history`

Returns the user job history stored in SQLite.

## Output behavior

- PDF input produces translated PDF output when `generate_output_file=true`.
- DOCX input produces translated DOCX output when `generate_output_file=true`.
- If output generation is disabled, only translated text is returned and stored.
- Progress is cleared when the job reaches `completed` or `failed`.
- Generated PDFs include visual QA metadata with a 98% similarity target. Text PDFs use coordinate-based cloning first and retry with a raster-background overlay when that improves visual similarity.

## OCR backend

When `force_ocr=true` or the PDF has no extractable text, Open WebUI uses OCR.

The translation helper now prefers GPU OCR when available:

- `OPEN_WEBUI_TRANSLATION_OCR_BACKEND=auto|paddle|rapidocr`
- `OPEN_WEBUI_TRANSLATION_OCR_USE_GPU=auto|true|false`
- `OPEN_WEBUI_TRANSLATION_OCR_LANGUAGE=en` by default

For GPU OCR, install PaddleOCR and a GPU-enabled PaddlePaddle build in the runtime environment.
