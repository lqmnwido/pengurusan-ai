# Membina Agentic AI V2T dengan OpenClaw, LangGraph dan Temporal

Reka bentuk ini mengikut pemisahan tanggungjawab projek `temporal-worker`:

- OpenClaw menyimpan identiti dan arahan setiap agent.
- LangGraph menyimpan susunan agent dalam aliran.
- Temporal menjalankan setiap langkah, retry, heartbeat dan progress.
- Worker menjalankan faster-whisper, Pyannote dan analisis LLM.
- MinIO menyimpan input dan artefak JSON selepas setiap langkah.

Agent bukan pemasangan model. Contohnya, `agent-transkripsi` ialah pemilik langkah
transkripsi, manakala pilihan `small` atau `large-v3` menentukan model
faster-whisper yang worker akan jalankan.

## 1. Pastikan perkhidmatan asas tersedia

Dalam `.env` Pengurusan AI, semak sekurang-kurangnya:

```dotenv
OPENCLAW_ENABLED='true'
TEMPORAL_ENABLED='true'
TEMPORAL_ADDRESS='127.0.0.1:7233'
TEMPORAL_NAMESPACE='default'
TEMPORAL_TASK_QUEUE='pengurusan-ai-agents'
STORAGE_PROVIDER='s3'
S3_ENDPOINT_URL='http://127.0.0.1:9000'
S3_BUCKET_NAME='open-webui'
HF_TOKEN='token-hugging-face-anda'
AGENTIC_MCP_TOKEN='jana-rahsia-panjang-dan-unik'
```

Jalankan aplikasi:

```bash
cd /home/lqmnwido/Projects/pengurusan-ai
make setup
make dev
```

## 2. Cipta enam agent OpenClaw

Jika OpenClaw melaporkan konfigurasi lama tidak sah, buat salinan sandaran fail
`backend/data/openclaw/openclaw.json`, kemudian jalankan `openclaw doctor --fix`
dan semak perubahan sebelum meneruskan.

Muatkan lokasi OpenClaw yang sama dengan Pengurusan AI:

```bash
cd /home/lqmnwido/Projects/pengurusan-ai
set -a
source .env
set +a
export OPENCLAW_HOME="${OPENCLAW_HOME:-$PWD/backend/data/openclaw}"
export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR:-$OPENCLAW_HOME}"
export OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$OPENCLAW_STATE_DIR/openclaw.json}"
export OPENCLAW_WORKSPACE_ROOT="${OPENCLAW_WORKSPACE_ROOT:-$OPENCLAW_STATE_DIR/workspaces}"
```

Gantikan model contoh dengan model LLM OpenClaw yang telah berfungsi. Model ini
digunakan oleh agent analisis; model Whisper dan Pyannote dipilih kemudian dalam
aliran.

```bash
openclaw agents add agent-transkripsi --non-interactive --workspace "$OPENCLAW_WORKSPACE_ROOT/agent-transkripsi" --model ollama/gemma4:e2b
openclaw agents add agent-diarisasi --non-interactive --workspace "$OPENCLAW_WORKSPACE_ROOT/agent-diarisasi" --model ollama/gemma4:e2b
openclaw agents add agent-chunking --non-interactive --workspace "$OPENCLAW_WORKSPACE_ROOT/agent-chunking" --model ollama/gemma4:e2b
openclaw agents add agent-topik --non-interactive --workspace "$OPENCLAW_WORKSPACE_ROOT/agent-topik" --model ollama/gemma4:e2b
openclaw agents add agent-ringkasan --non-interactive --workspace "$OPENCLAW_WORKSPACE_ROOT/agent-ringkasan" --model ollama/gemma4:e2b
openclaw agents add agent-tematik --non-interactive --workspace "$OPENCLAW_WORKSPACE_ROOT/agent-tematik" --model ollama/gemma4:e2b
```

Semak hasilnya:

```bash
openclaw agents list
```

## 3. Tetapkan arahan agent

Dalam setiap workspace, isi `IDENTITY.md` dan `SOUL.md`. Gunakan kontrak ringkas
berikut:

| Agent               | Tanggungjawab                                           | Larangan utama                         |
| ------------------- | ------------------------------------------------------- | -------------------------------------- |
| `agent-transkripsi` | Pemilik node faster-whisper dan transkrip bertanda masa | Jangan meringkaskan atau mengubah kata |
| `agent-diarisasi`   | Pemilik node label penutur                              | Jangan mereka identiti sebenar penutur |
| `agent-chunking`    | Pemilik saiz chunk dan overlap                          | Jangan membuang kandungan              |
| `agent-topik`       | Ekstrak topik dan bukti                                 | Jangan mereka topik tanpa bukti        |
| `agent-ringkasan`   | Keputusan, isu, tindakan, pegawai dan tarikh            | Jangan mereka fakta atau tarikh        |
| `agent-tematik`     | Tema, subtema dan petikan bukti                         | Jangan menggabungkan tema tanpa bukti  |

Contoh `SOUL.md` untuk `agent-ringkasan`:

```markdown
# Pegawai Ringkasan

Ringkaskan transkrip dalam Bahasa Melayu. Keluarkan ringkasan, keputusan, isu
utama, tindakan susulan, pegawai bertanggungjawab dan tarikh akhir. Jangan
mereka fakta. Gunakan "Tidak dinyatakan" apabila maklumat tiada. Jangan akses
fail atau sistem lain kecuali input yang diberikan oleh workflow.
```

Agent transkripsi, diarisasi dan chunking masih perlu wujud sebagai pemilik node,
tetapi kerja ML deterministik dilaksanakan oleh worker Temporal. Agent topik,
ringkasan dan tematik benar-benar dipanggil melalui OpenClaw oleh activity node.

## 4. Segerakkan agent ke Pengurusan AI

1. Buka `http://localhost:5173/agents`.
2. Tekan **Sync**.
3. Pastikan keenam-enam agent dipaparkan.
4. Pilih model utama bagi agent topik, ringkasan dan tematik.
5. Tetapkan semua agent yang digunakan kepada **Aktif**, kemudian tekan
   **Simpan**.

## 5. Bina aliran agent

1. Buka **Konfigurasi Agentic AI**.
2. Tekan **+ Baharu**.
3. Isi nama dan nama tool, contohnya `proses_voice_intelligence`.
4. Dalam **Agent tersedia**, klik hanya agent yang sudah wujud dalam OpenClaw.
   Urutan klik menjadi urutan awal workflow.
5. Contohnya, klik `pegawai-ringkasan` kemudian `main`. Output
   `pegawai-ringkasan` akan menjadi input tambahan kepada `main`.
6. Pilih model berasingan bagi setiap baris. Agent yang dikesan sebagai
   transkripsi memaparkan varian Whisper; agent lain memaparkan model LLM.
7. Gunakan anak panah untuk menukar urutan dan isi arahan tambahan jika perlu.
8. Aktifkan **Papar dalam chat**, tetapkan timeout/retry, kemudian tekan
   **Simpan**.
9. Mulakan chat baharu dan pilih nama aliran tersebut daripada pemilih model.

## 6. Penggunaan MCP pilihan

Workflow yang disimpan terus tersedia dalam chat. MCP hanya diperlukan jika
sistem luar atau agent OpenClaw perlu memanggil workflow sebagai tool:

```bash
make openclaw-agentic-mcp AGENT_ID=pegawai-ringkasan
```

Restart OpenClaw Gateway selepas pendaftaran.

## 7. Kesepadanan dengan projek temporal-worker

Projek rujukan mendaftarkan:

```text
AsrWorkflow::start       -> ASR_WORKFLOW_QUEUE
MediaActivities         -> MEDIA_TASK_QUEUE
ASR/Diarization/Analysis-> ASR_TASK_QUEUE
MinIO input             -> inputObjectKey
MinIO output            -> transcript JSON/SRT/VTT dan hasil analisis
```

Input Java yang tepat ialah:

```json
{
	"jobId": "meeting-2026-001",
	"inputObjectKey": "uploads/meeting.wav",
	"mediaTaskQueue": "MEDIA_TASK_QUEUE",
	"asrTaskQueue": "ASR_TASK_QUEUE",
	"targetBucket": "asr-poc"
}
```

Aliran asalnya ialah normalize audio, chunk audio, transcribe setiap chunk,
diarize setiap chunk, merge, refine speakers, chunk transcript, topic, summary
dan thematic. Aliran agent generik tidak menggantikan sublangkah Java itu satu
demi satu. Jika hasil mesti tepat sama seperti projek rujukan, jalankan
`AsrWorkflow::start` pada
`ASR_WORKFLOW_QUEUE` menggunakan input di atas; worker Java akan mengurus semua
sublangkah, progress, retry dan output MinIO. Gunakan aliran agent LangGraph
apabila topik, ringkasan dan tematik perlu dilaksanakan oleh agent OpenClaw yang
berbeza.
