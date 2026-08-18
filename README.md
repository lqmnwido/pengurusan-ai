<p align="center">
  <img src="https://dev.d-reams.com/img/logo-d.7378c4bf.png" alt="Pengurusan AI" width="72" />
</p>

<h1 align="center">Pengurusan AI</h1>

<p align="center">Platform AI beragent dengan OpenClaw, LangGraph, Temporal, PostgreSQL dan MinIO.</p>

## Architecture

| Component             | Responsibility                                                      |
| --------------------- | ------------------------------------------------------------------- |
| Pengurusan AI         | Web application, chat, models and agent administration              |
| OpenClaw              | Agent identity, instructions, workspace, skills and model execution |
| LangGraph             | Compiles the ordered flow configured in **Konfigurasi Agentic AI**  |
| Temporal              | Durable execution, progress, retry and cancellation                 |
| PostgreSQL + pgvector | Application data and vector retrieval                               |
| MinIO                 | Uploaded files and workflow artifacts                               |

LangGraph is installed as a Python dependency by `make setup`; it is not a
separate server. OpenClaw remains the source of truth for agent definitions.

## Supported operating systems

| Operating system              | Supported path                                                     |
| ----------------------------- | ------------------------------------------------------------------ |
| Ubuntu, Debian and Pop!\_OS   | Native Bash development and production                             |
| macOS Intel and Apple Silicon | Native development; `launchd` or another supervisor for production |
| Windows 11                    | WSL2 with Ubuntu 24.04; run project commands inside WSL            |

Native Windows PowerShell is not the supported application runtime because the
project's `make` targets and service scripts use Bash. Windows developers still
access the application through `localhost` while its processes run in WSL2.

## Requirements

- Python 3.11 or 3.12 with `python3-venv`
- Node.js 22 and npm
- PostgreSQL with the `vector` extension
- MinIO and MinIO Client (`mc`)
- Temporal CLI locally, or a production Temporal service
- Git, `make`, FFmpeg and an OpenClaw-supported model provider

This guide uses native processes and does not require Docker.

## Local development

### 1. Install prerequisites for your OS

#### Ubuntu, Debian or Pop!\_OS

```bash
nvm install 22
nvm use 22

sudo apt update
sudo apt install -y curl wget git make ffmpeg python3.12 python3.12-venv \
  postgresql postgresql-contrib postgresql-16-pgvector
```

The pgvector package name must match the installed PostgreSQL major version.

#### macOS

Install Homebrew, then:

```bash
brew install bash node@22 python@3.12 postgresql@17 pgvector ffmpeg make
brew services start postgresql@17

export PATH="$(brew --prefix node@22)/bin:$PATH"
export PATH="$(brew --prefix python@3.12)/libexec/bin:$PATH"
export PATH="$(brew --prefix postgresql@17)/bin:$PATH"
```

Add those three `PATH` exports to `~/.zshrc` so future terminals use the same
versions. The Homebrew pgvector formula must match a supported Homebrew
PostgreSQL version.

#### Windows 11 with WSL2

Run in an Administrator PowerShell terminal:

```powershell
wsl --install -d Ubuntu-24.04
wsl --update
```

Restart Windows if requested, open the Ubuntu terminal, and follow the
**Ubuntu, Debian or Pop!\_OS** commands above. Clone the repository inside the
WSL filesystem, such as `~/Projects/pengurusan-ai`, rather than under `/mnt/c`,
for better file-watching and installation performance.

The Windows browser can open the WSL services through the same
`http://localhost:5173`, `:8080`, `:8233`, `:9000` and `:9001` addresses. For a
production-like WSL service setup, add this to `/etc/wsl.conf`:

```ini
[boot]
systemd=true
```

Run `wsl --shutdown` from PowerShell, restart Ubuntu, and use the Linux systemd
units later in this guide.

### 2. Configure PostgreSQL and pgvector

Linux or WSL2:

```bash
sudo -u postgres psql
```

macOS with Homebrew PostgreSQL:

```bash
psql postgres
```

Run:

```sql
CREATE USER openwebui WITH PASSWORD 'change-me';
CREATE DATABASE openwebui OWNER openwebui;
\connect openwebui
CREATE EXTENSION IF NOT EXISTS vector;
\quit
```

### 3. Start MinIO

#### Linux or WSL2

Install the official Linux AMD64 binaries. Replace `linux-amd64` with
`linux-arm64` on ARM:

```bash
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo install minio /usr/local/bin/minio

wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo install mc /usr/local/bin/mc
```

#### macOS

```bash
brew install minio/stable/minio
brew install minio/stable/mc
```

#### Start the server on any supported OS

Run MinIO in one terminal:

```bash
mkdir -p "$HOME/.local/share/pengurusan-ai/minio"
export MINIO_ROOT_USER='openwebui'
export MINIO_ROOT_PASSWORD='change-me-minio-secret'
minio server "$HOME/.local/share/pengurusan-ai/minio" \
  --address ':9000' \
  --console-address ':9001'
```

Create the bucket from another terminal:

```bash
mc alias set pengurusan-local http://127.0.0.1:9000 \
  openwebui change-me-minio-secret
mc mb --ignore-existing pengurusan-local/open-webui
```

- S3 API: `http://127.0.0.1:9000`
- Console: `http://127.0.0.1:9001`

### 4. Start Temporal

#### Linux or WSL2

Install the official Temporal CLI for Linux AMD64. Change `arch=amd64` to
`arch=arm64` on ARM:

```bash
curl -L 'https://temporal.download/cli/archive/latest?platform=linux&arch=amd64' \
  -o /tmp/temporal-cli.tar.gz
mkdir -p /tmp/temporal-cli
tar -xzf /tmp/temporal-cli.tar.gz -C /tmp/temporal-cli
sudo install /tmp/temporal-cli/temporal /usr/local/bin/temporal
temporal --version
```

#### macOS

```bash
brew install temporal
temporal --version
```

#### Start the development server on any supported OS

Run Temporal in a separate terminal:

```bash
mkdir -p "$HOME/.local/share/pengurusan-ai/temporal"
temporal server start-dev \
  --ip 127.0.0.1 \
  --port 7233 \
  --ui-port 8233 \
  --db-filename "$HOME/.local/share/pengurusan-ai/temporal/temporal.db"
```

- Temporal service: `127.0.0.1:7233`
- Temporal UI: `http://127.0.0.1:8233`

Do not use the development server in production.

### 5. Configure `.env`

```bash
git clone <repository-url> pengurusan-ai
cd pengurusan-ai
cp .env.example .env
openssl rand -hex 32
openssl rand -hex 32
```

Put the generated secrets and service credentials in `.env`:

```env
# PostgreSQL + pgvector
DATABASE_URL='postgresql://openwebui:change-me@127.0.0.1:5432/openwebui'
VECTOR_DB='pgvector'
PGVECTOR_DB_URL='postgresql://openwebui:change-me@127.0.0.1:5432/openwebui'

# MinIO
STORAGE_PROVIDER='s3'
STORAGE_LOCAL_CACHE='true'
S3_ENDPOINT_URL='http://127.0.0.1:9000'
S3_ACCESS_KEY_ID='openwebui'
S3_SECRET_ACCESS_KEY='change-me-minio-secret'
S3_BUCKET_NAME='open-webui'
S3_REGION_NAME='us-east-1'
S3_ADDRESSING_STYLE='path'

# Temporal
TEMPORAL_ENABLED='true'
TEMPORAL_ADDRESS='127.0.0.1:7233'
TEMPORAL_NAMESPACE='default'
TEMPORAL_TASK_QUEUE='pengurusan-ai-agents'
TEMPORAL_TLS='false'
TEMPORAL_API_KEY=''

# OpenClaw
OPENCLAW_ENABLED='false'
OPENCLAW_COMMAND='openclaw'
OPENCLAW_HOME='./backend/data/openclaw'
OPENCLAW_STATE_DIR='./backend/data/openclaw'
OPENCLAW_WORKSPACE_ROOT='./backend/data/openclaw/workspaces'

# Local Ollama, when used
OLLAMA_BASE_URL='http://127.0.0.1:11434'
OLLAMA_API_KEY='ollama-local'
OPENCLAW_OLLAMA_NUM_CTX='16384'

# Application security
WEBUI_SECRET_KEY='replace-with-the-first-generated-secret'
AGENTIC_MCP_TOKEN='replace-with-the-second-generated-secret'
AGENT_EXTERNAL_API_ENABLED='true'
CORS_ALLOW_ORIGIN='http://localhost:5173;http://localhost:8080'
FORWARDED_ALLOW_IPS='127.0.0.1'
```

Set `HF_TOKEN` only when the selected Pyannote model requires Hugging Face
access. Never commit `.env`.

### 6. Install dependencies

```bash
node --version  # must report v22.x
make setup
```

`make setup` creates `.venv`, installs the locked backend and frontend
dependencies, installs LangGraph and the Temporal SDK, and installs the pinned
OpenClaw CLI. You do not need to activate `.venv` manually.

### 7. Set up OpenClaw

Run onboarding as the same operating-system user that runs the application:

```bash
make openclaw-setup
```

During onboarding:

1. Accept the security notice.
2. Select and configure a model provider.
3. Keep the Gateway on loopback unless it is separately secured.
4. Confirm the selected model can answer a test prompt.

Then enable OpenClaw in `.env`:

```env
OPENCLAW_ENABLED='true'
```

If OpenClaw is installed through NVM, obtain and save its absolute path:

```bash
command -v openclaw
```

```env
OPENCLAW_COMMAND='/absolute/path/returned/by/command-v-openclaw'
```

Create and edit agents in OpenClaw. In Pengurusan AI, open **Konfigurasi
Agent**, press **Sync**, select a model, activate the agent and save.

### 8. Run Pengurusan AI

```bash
make dev
```

This starts:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8080`
- Temporal worker when `TEMPORAL_ENABLED=true`

Press `Ctrl+C` once to stop all application processes.

### 9. Configure a LangGraph workflow

1. Create the required agents in OpenClaw.
2. Synchronize and activate them in **Konfigurasi Agent**.
3. Open **Konfigurasi Agentic AI**.
4. Add active agents in the exact execution order.
5. Select the model and instruction for every step.
6. Save and activate the workflow.
7. Select the workflow in a new chat.

LangGraph compiles the saved order. Temporal executes each step sequentially
and reports progress, retry and cancellation. MinIO stores file inputs and
workflow artifacts.

## Production deployment

Use managed or separately supervised PostgreSQL, MinIO and Temporal services.
Do not expose PostgreSQL, MinIO, Temporal or the OpenClaw Gateway publicly.

| Production host | Process supervisor                                                     |
| --------------- | ---------------------------------------------------------------------- |
| Linux           | `systemd` reference below                                              |
| macOS           | `launchd`; run the same `make serve` and `make agent-worker` processes |
| Windows         | Deploy inside WSL2 with systemd, or preferably use a Linux VM/server   |

The application build and `.env` values are portable. Only service-account,
filesystem-path and process-supervisor instructions change by host OS.

### 1. Prepare a Linux production server

```bash
sudo useradd --system --create-home --shell /bin/bash pengurusan-ai
sudo mkdir -p /opt/pengurusan-ai /var/lib/pengurusan-ai/openclaw
sudo chown -R pengurusan-ai:pengurusan-ai \
  /opt/pengurusan-ai /var/lib/pengurusan-ai
```

Deploy the repository into `/opt/pengurusan-ai`. Install Python 3.11 or 3.12,
Node.js 22, FFmpeg and `make` system-wide. Configure a writable npm prefix for
the service account because `make setup` installs the pinned OpenClaw CLI:

```bash
sudo -H -u pengurusan-ai npm config set prefix /home/pengurusan-ai/.local
sudo -H -u pengurusan-ai mkdir -p /home/pengurusan-ai/.local/bin
```

### 2. Prepare production services

1. Create the PostgreSQL database and run `CREATE EXTENSION vector`.
2. Create a private MinIO bucket and least-privilege application access key.
3. Create a Temporal namespace and allow the worker to poll the
   `pengurusan-ai-agents` task queue.
4. Restrict all service ports to the application network.
5. Use TLS for connections crossing a trusted host boundary.

For Temporal Cloud, use its endpoint, namespace and API key with
`TEMPORAL_TLS=true`.

### 3. Create the production `.env`

```bash
cd /opt/pengurusan-ai
cp .env.example .env
chmod 600 .env
```

Replace every example secret:

```env
DATABASE_URL='postgresql://pengurusan:strong-password@postgres.internal:5432/pengurusan_ai'
VECTOR_DB='pgvector'
PGVECTOR_DB_URL='postgresql://pengurusan:strong-password@postgres.internal:5432/pengurusan_ai'

STORAGE_PROVIDER='s3'
STORAGE_LOCAL_CACHE='true'
S3_ENDPOINT_URL='https://minio.internal'
S3_ACCESS_KEY_ID='pengurusan-ai'
S3_SECRET_ACCESS_KEY='replace-with-minio-secret'
S3_BUCKET_NAME='pengurusan-ai'
S3_REGION_NAME='us-east-1'
S3_ADDRESSING_STYLE='path'

TEMPORAL_ENABLED='true'
TEMPORAL_ADDRESS='temporal.internal:7233'
TEMPORAL_NAMESPACE='pengurusan-ai'
TEMPORAL_TASK_QUEUE='pengurusan-ai-agents'
TEMPORAL_TLS='true'
TEMPORAL_API_KEY='replace-when-required'

OPENCLAW_ENABLED='true'
OPENCLAW_COMMAND='/home/pengurusan-ai/.local/bin/openclaw'
OPENCLAW_HOME='/var/lib/pengurusan-ai/openclaw'
OPENCLAW_STATE_DIR='/var/lib/pengurusan-ai/openclaw'
OPENCLAW_WORKSPACE_ROOT='/var/lib/pengurusan-ai/openclaw/workspaces'

WEBUI_SECRET_KEY='replace-with-a-long-random-secret'
AGENTIC_MCP_TOKEN='replace-with-a-different-random-secret'
AGENT_EXTERNAL_API_ENABLED='true'
CORS_ALLOW_ORIGIN='https://ai.example.gov.my'
FORWARDED_ALLOW_IPS='127.0.0.1'
HOST='127.0.0.1'
PORT='8080'
UVICORN_WORKERS='1'
```

Use absolute OpenClaw paths and keep its state outside the release directory.
Keep `UVICORN_WORKERS=1` unless multiple web workers have been tested.

### 4. Install, onboard and build

Run as the production service account:

```bash
sudo -iu pengurusan-ai
cd /opt/pengurusan-ai
make setup
make openclaw-setup
make build
```

Confirm `.env` has `OPENCLAW_ENABLED=true` and the correct absolute CLI and
state paths after onboarding.

### 5. Install systemd services

This subsection applies to Linux and systemd-enabled WSL2. On macOS, create two
equivalent `launchd` jobs with `/opt/pengurusan-ai` as `WorkingDirectory`:

- Web process: `/usr/bin/make serve`
- Temporal worker: `/usr/bin/make agent-worker`

Set both jobs to restart on failure and load the same production `.env`. Use
`command -v make` if `make` is not `/usr/bin/make` on macOS. The job `PATH`
must include the Homebrew `bin` directory so Node.js 22 and Homebrew Bash are
used.

Create `/etc/systemd/system/pengurusan-ai.service`:

```ini
[Unit]
Description=Pengurusan AI web application
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pengurusan-ai
Group=pengurusan-ai
WorkingDirectory=/opt/pengurusan-ai
ExecStart=/usr/bin/make serve
Restart=on-failure
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/pengurusan-ai-worker.service`:

```ini
[Unit]
Description=Pengurusan AI Temporal worker
After=network-online.target pengurusan-ai.service
Wants=network-online.target

[Service]
Type=simple
User=pengurusan-ai
Group=pengurusan-ai
WorkingDirectory=/opt/pengurusan-ai
ExecStart=/usr/bin/make agent-worker
Restart=on-failure
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

Enable both services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pengurusan-ai
sudo systemctl enable --now pengurusan-ai-worker
sudo systemctl status pengurusan-ai pengurusan-ai-worker
```

Place Nginx, Caddy or another TLS reverse proxy in front of
`http://127.0.0.1:8080`. Enable WebSocket upgrades and configure an upload limit
suitable for audio and document files.

### 6. Verify production

```bash
curl --fail http://127.0.0.1:8080/health
sudo journalctl -u pengurusan-ai -u pengurusan-ai-worker -f
```

Then verify in the browser:

1. **Konfigurasi Agent** reports OpenClaw available.
2. Agent synchronization and activation work.
3. A test file reaches MinIO.
4. A two-agent chat workflow completes in queue order.
5. The workflow and activities appear in Temporal UI.

### 7. Deploy an update

Back up PostgreSQL, MinIO and the OpenClaw state directory first:

```bash
cd /opt/pengurusan-ai
git pull --ff-only
make deploy
sudo systemctl restart pengurusan-ai pengurusan-ai-worker
curl --fail http://127.0.0.1:8080/health
```

Database migrations run during backend startup. Never remove a migration that
may already have been applied.

## Essential commands

| Command               | Purpose                                                                 |
| --------------------- | ----------------------------------------------------------------------- |
| `make help`           | Show all project commands                                               |
| `make setup`          | Create `.env`/`.venv` and install application and OpenClaw dependencies |
| `make openclaw-setup` | Run OpenClaw provider and authentication onboarding                     |
| `make dev`            | Run frontend, backend and the enabled Temporal worker                   |
| `make build`          | Build the production frontend into `build/`                             |
| `make serve`          | Serve the production frontend and API on port 8080                      |
| `make agent-worker`   | Run the Temporal worker separately                                      |
| `make deploy`         | Run setup and build for a release                                       |

For the complete Voice-to-Text workflow, see
[docs/agentic-ai-voice-workflow.md](docs/agentic-ai-voice-workflow.md).
