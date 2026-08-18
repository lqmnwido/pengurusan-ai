# Open WebUI 👋

![GitHub stars](https://img.shields.io/github/stars/open-webui/open-webui?style=social)
![GitHub forks](https://img.shields.io/github/forks/open-webui/open-webui?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/open-webui/open-webui?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/open-webui/open-webui)
![GitHub language count](https://img.shields.io/github/languages/count/open-webui/open-webui)
![GitHub top language](https://img.shields.io/github/languages/top/open-webui/open-webui)
![GitHub last commit](https://img.shields.io/github/last-commit/open-webui/open-webui?color=red)
[![Discord](https://img.shields.io/badge/Discord-Open_WebUI-blue?logo=discord&logoColor=white)](https://discord.gg/5rJgQTnV4s)
[![](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/tjbck)

![Open WebUI Banner](./banner.png)

**Open WebUI is an [extensible](https://docs.openwebui.com/features/extensibility/plugin), feature-rich, and user-friendly self-hosted AI platform designed to operate entirely offline.** It supports various LLM runners like **Ollama** and **OpenAI-compatible APIs**, with **built-in inference engine** for RAG, making it a **powerful AI deployment solution**.

Passionate about open-source AI? [Join our team →](https://careers.openwebui.com/)

![Open WebUI Demo](./demo.png)

> [!TIP]  
> **Looking for an [Enterprise Plan](https://docs.openwebui.com/enterprise)?** – **[Speak with Our Sales Team Today!](https://docs.openwebui.com/enterprise)**
>
> Get **enhanced capabilities**, including **custom theming and branding**, **Service Level Agreement (SLA) support**, **Long-Term Support (LTS) versions**, and **more!**

For more information, be sure to check out our [Open WebUI Documentation](https://docs.openwebui.com/).

## Key Features of Open WebUI ⭐

- 🚀 **Effortless Setup**: Install seamlessly using Docker or Kubernetes (kubectl, kustomize or helm) for a hassle-free experience with support for both `:ollama` and `:cuda` tagged images.

- 🤝 **Ollama/OpenAI API Integration**: Effortlessly integrate OpenAI-compatible APIs for versatile conversations alongside Ollama models. Customize the OpenAI API URL to link with **LMStudio, GroqCloud, Mistral, OpenRouter, and more**.

- 🛡️ **Granular Permissions and User Groups**: By allowing administrators to create detailed user roles and permissions, we ensure a secure user environment. This granularity not only enhances security but also allows for customized user experiences, fostering a sense of ownership and responsibility amongst users.

- 📱 **Responsive Design**: Enjoy a seamless experience across Desktop PC, Laptop, and Mobile devices.

- 📱 **Progressive Web App (PWA) for Mobile**: Enjoy a native app-like experience on your mobile device with our PWA, providing offline access on localhost and a seamless user interface.

- ✒️🔢 **Full Markdown and LaTeX Support**: Elevate your LLM experience with comprehensive Markdown and LaTeX capabilities for enriched interaction.

- 🎤📹 **Hands-Free Voice/Video Call**: Experience seamless communication with integrated hands-free voice and video call features using multiple Speech-to-Text providers (Local Whisper, OpenAI, Deepgram, Azure) and Text-to-Speech engines (Azure, ElevenLabs, OpenAI, Transformers, WebAPI), allowing for dynamic and interactive chat environments.

- 🛠️ **Model Builder**: Easily create Ollama models via the Web UI. Create and add custom characters/agents, customize chat elements, and import models effortlessly through [Open WebUI Community](https://openwebui.com/) integration.

- 🐍 **Native Python Function Calling Tool**: Enhance your LLMs with built-in code editor support in the tools workspace. Bring Your Own Function (BYOF) by simply adding your pure Python functions, enabling seamless integration with LLMs.

- 💾 **Persistent Artifact Storage**: Built-in key-value storage API for artifacts, enabling features like journals, trackers, leaderboards, and collaborative tools with both personal and shared data scopes across sessions.

- 📚 **Local RAG Integration**: Dive into the future of chat interactions with groundbreaking Retrieval Augmented Generation (RAG) support using your choice of 9 vector databases and multiple content extraction engines (Tika, Docling, Document Intelligence, Mistral OCR, PaddleOCR-vl, External loaders). Load documents directly into chat or add files to your document library, effortlessly accessing them using the `#` command before a query.

- 🌍 **Document Translation**: Translate uploaded DOCX and PDF files with a TranslateGemma model, including text PDFs via PyMuPDF and scanned PDFs via OCRmyPDF or PaddleOCR-vl, then generate translated DOCX/PDF files for download and side-by-side review. See [Document Translation](./docs/DOCUMENT_TRANSLATION.md).

- 🔍 **Web Search for RAG**: Perform web searches using 15+ providers including `SearXNG`, `Google PSE`, `Brave Search`, `Kagi`, `Mojeek`, `Tavily`, `Perplexity`, `serpstack`, `serper`, `Serply`, `DuckDuckGo`, `SearchApi`, `SerpApi`, `Bing`, `Jina`, `Exa`, `Sougou`, `Azure AI Search`, and `Ollama Cloud`, injecting results directly into your chat experience.

- 🌐 **Web Browsing Capability**: Seamlessly integrate websites into your chat experience using the `#` command followed by a URL. This feature allows you to incorporate web content directly into your conversations, enhancing the richness and depth of your interactions.

- 🎨 **Image Generation & Editing Integration**: Create and edit images using multiple engines including OpenAI's DALL-E, Gemini, ComfyUI (local), and AUTOMATIC1111 (local), with support for both generation and prompt-based editing workflows.

- ⚙️ **Many Models Conversations**: Effortlessly engage with various models simultaneously, harnessing their unique strengths for optimal responses. Enhance your experience by leveraging a diverse set of models in parallel.

- 🔐 **Role-Based Access Control (RBAC)**: Ensure secure access with restricted permissions; only authorized individuals can access your Ollama, and exclusive model creation/pulling rights are reserved for administrators.

- 🗄️ **Flexible Database & Storage Options**: Choose from SQLite (with optional encryption), PostgreSQL, or configure cloud storage backends (S3, Google Cloud Storage, Azure Blob Storage) for scalable deployments.

- 🔍 **Advanced Vector Database Support**: Select from 9 vector database options including ChromaDB, PGVector, Qdrant, Milvus, Elasticsearch, OpenSearch, Pinecone, S3Vector, and Oracle 23ai for optimal RAG performance.

- 🔐 **Enterprise Authentication**: Full support for LDAP/Active Directory integration, SCIM 2.0 automated provisioning, and SSO via trusted headers alongside OAuth providers. Enterprise-grade user and group provisioning through SCIM 2.0 protocol, enabling seamless integration with identity providers like Okta, Azure AD, and Google Workspace for automated user lifecycle management.

- ☁️ **Cloud-Native Integration**: Native support for Google Drive and OneDrive/SharePoint file picking, enabling seamless document import from enterprise cloud storage.

- 📊 **Production Observability**: Built-in OpenTelemetry support for traces, metrics, and logs, enabling comprehensive monitoring with your existing observability stack.

- ⚖️ **Horizontal Scalability**: Redis-backed session management and WebSocket support for multi-worker and multi-node deployments behind load balancers.

- 🌐🌍 **Multilingual Support**: Experience Open WebUI in your preferred language with our internationalization (i18n) support. Join us in expanding our supported languages! We're actively seeking contributors!

- 🧩 **Pipelines, Open WebUI Plugin Support**: Seamlessly integrate custom logic and Python libraries into Open WebUI using [Pipelines Plugin Framework](https://github.com/open-webui/pipelines). Launch your Pipelines instance, set the OpenAI URL to the Pipelines URL, and explore endless possibilities. [Examples](https://github.com/open-webui/pipelines/tree/main/examples) include **Function Calling**, User **Rate Limiting** to control access, **Usage Monitoring** with tools like Langfuse, **Live Translation with LibreTranslate** for multilingual support, **Toxic Message Filtering** and much more.

- 🌟 **Continuous Updates**: We are committed to improving Open WebUI with regular updates, fixes, and new features.

Want to learn more about Open WebUI's features? Check out our [Open WebUI documentation](https://docs.openwebui.com/features) for a comprehensive overview!

---

We are incredibly grateful for the generous support of our sponsors. Their contributions help us to maintain and improve our project, ensuring we can continue to deliver quality work to our community. Thank you!

## How to Install 🚀

### Native development and production (without Docker)

This is the recommended workflow for Pengurusan AI. The application runs directly
on the host; PostgreSQL, MinIO, Temporal, and model servers are separate local or
managed services.

#### Requirements

- Linux server or development machine
- Node.js 22 and npm
- Python 3.11 or 3.12, including the `venv` module
- PostgreSQL with the `pgvector` extension
- MinIO or another S3-compatible object store
- Temporal server when durable agent workflows are enabled

List every supported command at any time:

```bash
make help
```

#### Make command reference

| Command               | Purpose                                                                                                                                    | When to run                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------- |
| `make help`           | Displays every Make command without changing the environment.                                                                              | Any time                                             |
| `make setup`          | Creates `.env` when missing, recreates/updates `.venv`, installs locked Python and npm dependencies, and installs the pinned OpenClaw CLI. | First install and after dependency changes           |
| `make dev`            | Runs Vite on 5173, the reloadable API on 8080, and the agent worker when `TEMPORAL_ENABLED=true`.                                          | Local development                                    |
| `make build`          | Downloads/prepares Pyodide when required and builds the frontend into `build/`.                                                            | Before production serving                            |
| `make serve`          | Runs the production backend without reload and serves the built frontend and API on port 8080.                                             | Production web process                               |
| `make agent-worker`   | Runs the Pengurusan AI Temporal worker on `TEMPORAL_TASK_QUEUE`.                                                                           | Separate production process when Temporal is enabled |
| `make openclaw-setup` | Starts the one-time OpenClaw provider and authentication onboarding.                                                                       | Once per environment, before enabling OpenClaw       |
| `make deploy`         | Runs `make setup` followed by `make build`. It does not start or restart services.                                                         | Initial production install or release deployment     |
| `make install`        | Starts the legacy Docker Compose deployment.                                                                                               | Docker users only                                    |
| `make start`          | Starts existing Docker Compose services.                                                                                                   | Docker users only                                    |
| `make startAndBuild`  | Builds and starts Docker Compose services.                                                                                                 | Docker users only                                    |
| `make stop`           | Stops Docker Compose services.                                                                                                             | Docker users only                                    |
| `make remove`         | Runs the confirmation-based Docker removal script.                                                                                         | Docker users only                                    |
| `make update`         | Updates Ollama models and source, then rebuilds Docker services.                                                                           | Docker users only                                    |

Running `make` without a target displays the same help and does not install or
start anything.

#### Local developer installation

For the first local setup, create and configure `.env`, then install the locked frontend and backend dependencies:

```bash
git clone <repository-url> pengurusan-ai
cd pengurusan-ai
nvm use 22
cp .env.example .env
# Update DATABASE_URL, PGVECTOR_DB_URL, MinIO credentials, and WEBUI_SECRET_KEY.
make setup
```

`make setup` creates and manages `.venv`; developers do not need to activate it
manually. Ensure PostgreSQL and MinIO are running, then start both application
processes:

Run the frontend and backend together for local development:

```bash
make dev
```

The frontend is available at `http://localhost:5173` and the backend at `http://localhost:8080`. Press `Ctrl+C` once to stop both.

#### Native production deployment

Use a dedicated non-root service account and a stable checkout path. PostgreSQL,
MinIO, and (when enabled) Temporal must be reachable using the addresses in
`.env`. Do not commit `.env`.

Create production configuration and use unique passwords and a long random
secret:

```bash
cp .env.example .env
openssl rand -hex 32
# Put the generated value in WEBUI_SECRET_KEY and configure the service URLs.
```

Recommended production overrides include:

```env
DATABASE_URL='postgresql://openwebui:strong-password@127.0.0.1:5432/openwebui'
PGVECTOR_DB_URL='postgresql://openwebui:strong-password@127.0.0.1:5432/openwebui'
STORAGE_PROVIDER='s3'
S3_ENDPOINT_URL='http://127.0.0.1:9000'
S3_ACCESS_KEY_ID='openwebui'
S3_SECRET_ACCESS_KEY='strong-minio-password'
S3_BUCKET_NAME='open-webui'
WEBUI_SECRET_KEY='replace-with-the-generated-random-value'
CORS_ALLOW_ORIGIN='https://ai.example.com'
FORWARDED_ALLOW_IPS='127.0.0.1'
HOST='127.0.0.1'
PORT='8080'
UVICORN_WORKERS='1'
```

Keep `UVICORN_WORKERS=1` unless the deployment has been explicitly tested with
multiple application workers. Install dependencies and build the release:

```bash
make deploy
```

Run it directly for a first verification:

```bash
make serve
```

Check `http://127.0.0.1:8080/health`, then stop it and configure a process
supervisor. Example `/etc/systemd/system/pengurusan-ai.service`:

```ini
[Unit]
Description=Pengurusan AI web application
After=network-online.target postgresql.service
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

If Temporal agents are enabled, create a second service at
`/etc/systemd/system/pengurusan-ai-worker.service`:

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

Enable the required processes after replacing the example user and path with
the real deployment values:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pengurusan-ai
sudo systemctl enable --now pengurusan-ai-worker  # only when Temporal is enabled
sudo systemctl status pengurusan-ai
```

Place Nginx, Caddy, or another TLS reverse proxy in front of
`http://127.0.0.1:8080`. The public proxy must support WebSocket upgrade headers
and should enforce an upload-size limit appropriate for audio and document
agents.

To deploy a later release:

```bash
git pull --ff-only
make deploy
sudo systemctl restart pengurusan-ai
sudo systemctl restart pengurusan-ai-worker  # when enabled
```

Database migrations run during backend startup. Back up PostgreSQL and MinIO
before deploying a new release, and never delete an Alembic migration that may
already have been applied.

#### AI Agent orchestration

OpenClaw is the source of truth for agent identity, instructions, tools, skills,
workspaces and routing. Create or modify agents in OpenClaw. Administrators use
**Konfigurasi Agent** only to synchronize that registry, select a model already
registered under **Workspace → Models**, activate/deactivate Pengurusan AI
access, and issue an API key for an external system.

OpenClaw is installed globally at the version pinned by `make setup`. Complete
its one-time provider/auth onboarding, then enable the integration:

```bash
make setup
make openclaw-setup
```

```env
OPENCLAW_ENABLED=true
OPENCLAW_COMMAND='/absolute/path/from-command-v-openclaw'
OPENCLAW_STATE_DIR=./backend/data/openclaw
OPENCLAW_WORKSPACE_ROOT=./backend/data/openclaw/workspaces
```

Obtain the executable path with `command -v openclaw`. Use the absolute path in
production, especially when Node.js is managed by NVM, because systemd does not
load the deployment user's interactive shell configuration.

Create an agent from the OpenClaw setup interface or CLI, then press **Sync** in
**Konfigurasi Agent**. Deleting an agent must also be done in OpenClaw; the next
sync removes it from the active Pengurusan AI list and revokes its external API
key.

The external endpoint is deliberately narrower than the OpenClaw Gateway API:

```text
POST /api/v1/agents/external/{pengurusan_agent_id}/invoke
Authorization: Bearer pai_...
Content-Type: application/json
```

```json
{
	"message": "Summarize this incident",
	"session_key": "external-system-conversation-123"
}
```

Generate or rotate the bearer key in **Konfigurasi Agent**. The full key is shown
once and only its SHA-256 hash is stored. Each key is scoped to one active agent;
never give an external application the OpenClaw Gateway operator token. In
production, expose this endpoint only over TLS and apply request/rate limits at
the reverse proxy. Disable all external agent calls with:

```env
AGENT_EXTERNAL_API_ENABLED=false
```

Pengurusan AI stores only the OpenClaw link, selected model, active state and
hashed external credential in PostgreSQL. Agent definitions remain in OpenClaw.
Agent file outputs use the configured storage provider, so the native MinIO
setup requires:

```env
STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=http://127.0.0.1:9000
S3_BUCKET_NAME=open-webui
```

For durable execution, run a Temporal server and configure:

```env
TEMPORAL_ENABLED=true
TEMPORAL_ADDRESS=127.0.0.1:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=pengurusan-ai-agents
```

Start the Temporal worker as a separate supervised process:

```bash
make agent-worker
```

The worker exposes `pengurusan_ai.agent.run`, `pengurusan_ai.openclaw.chat`, and
`pengurusan_ai.voice.v2t`. OpenClaw owns the agent definition, LangGraph compiles
the configured Voice Intelligence graph, and Temporal executes every graph node
as a durable activity. MinIO stores file inputs and a new JSON artifact after
each node, rather than putting large transcripts into Temporal history.

To test an agent in the normal chat locally:

1. Start Temporal and set `TEMPORAL_ENABLED=true` in `.env`.
2. Run `make dev`; it starts the web processes and agent worker together.
3. Open **Konfigurasi Agent**, synchronize OpenClaw, choose a model, and set the
   agent to active.
4. Start a new chat and select the agent by name. It appears with the
   **Agent OpenClaw** and **Temporal** tags.

The active setting publishes the agent to signed-in chat users. Disabling it
removes it from the model selector and rejects new workflow executions.

#### Configurable V2T workflow

Tutorial langkah demi langkah untuk mencipta agent Transkripsi, Diarisasi,
Chunking, Topik, Ringkasan dan Tematik serta memadankannya dengan kontrak projek
`temporal-worker` tersedia dalam
[Agentic AI Voice Workflow](docs/agentic-ai-voice-workflow.md).

Agent settings and agentic workflows are deliberately separate:

- **Konfigurasi Agent** synchronizes OpenClaw agents and manages their main
  model, active status, and external API key.
- **Konfigurasi Agentic AI** arranges existing synchronized OpenClaw agents into
  an ordered LangGraph workflow. Saving an active workflow publishes it in the
  normal chat model selector.

In **Konfigurasi Agentic AI**, click existing agents in the required order, then
choose a model and optional instruction for every node. For example,
`pegawai-ringkasan` followed by `main` runs the summarizer first and passes its
output to `main` before returning the final chat response.

1. **Transkripsi** — a faster-whisper variant such as `small` or `large-v3`.
2. **Diarisasi** — Pyannote Community-1 in the native Python worker, or the
   SpeechBrain + Silero profile in the external `temporal-worker` deployment.
3. **Pecahan transkrip** — prepares bounded chunks for long recordings.
4. **Topik** — extracts topics and evidence through its assigned OpenClaw agent.
5. **Ringkasan** — uses its assigned OpenClaw agent and selected model.
6. **Analisis tematik** — may use a different agent and model.

Whisper remains the first required node. The remaining selected nodes can be
reordered because each Temporal activity reads the latest saved artifact. To
run the native flow, upload an audio file through the platform file store and
invoke:

```text
POST /api/v1/agentic-workflows/{workflow_id}/run
{"file_path":"<platform storage path>","job_id":"meeting-2026-001"}
```

The start response contains `workflow_id`. Poll durable progress with:

```text
GET /api/v1/agentic-workflows/runs/{workflow_id}/status
```

The response reports `current_step`, `progress`, completed/total steps, and the
latest MinIO `artifact_path`. For Pyannote, install the component from the AI
component manager, accept its Hugging Face terms, and configure `HF_TOKEN`.

To expose active workflows as MCP tools to an allowed OpenClaw agent, configure
a unique `AGENTIC_MCP_TOKEN`, start the Pengurusan AI API, then register the
agent-scoped bridge:

```bash
make openclaw-agentic-mcp AGENT_ID=pegawai-ringkasan
```

Restart the OpenClaw Gateway after changing MCP configuration. The bridge reads
only workflows whose allowlist contains that OpenClaw agent ID. A selected
workflow is advertised as one tool; Whisper, Pyannote, chunking, topic, summary,
and thematic nodes remain internal and do not appear as separate tools in every agent.
Disabled workflows are not advertised. The backend rechecks the allowlist when
the tool is invoked.

Temporal remains responsible for durable media/file workflows such as the external voice/diarization profile modelled after `temporal-worker`:

```text
workflow:    AsrWorkflow::start
workflow q:  ASR_WORKFLOW_QUEUE
media q:     MEDIA_TASK_QUEUE
ASR q:       ASR_TASK_QUEUE
input:       MinIO object key
output:      transcript JSON/SRT/VTT, chunks and analysis artifacts in MinIO
```

That profile sends the worker-compatible camel-case input fields (`jobId`, `inputObjectKey`, `mediaTaskQueue`, `asrTaskQueue`, and `targetBucket`). It keeps model execution in the dedicated workers while Pengurusan AI owns agent configuration, authorization, storage selection, and workflow dispatch.

### Installation via Python pip 🐍

Open WebUI can be installed using pip, the Python package installer. Before proceeding, ensure you're using **Python 3.11** to avoid compatibility issues.

1. **Install Open WebUI**:
   Open your terminal and run the following command to install Open WebUI:

   ```bash
   pip install open-webui
   ```

2. **Running Open WebUI**:
   After installation, you can start Open WebUI by executing:

   ```bash
   open-webui serve
   ```

This will start the Open WebUI server, which you can access at [http://localhost:8080](http://localhost:8080)

### Quick Start with Docker 🐳

> [!NOTE]  
> Please note that for certain Docker environments, additional configurations might be needed. If you encounter any connection issues, our detailed guide on [Open WebUI Documentation](https://docs.openwebui.com/) is ready to assist you.

> [!WARNING]
> When using Docker to install Open WebUI, make sure to include the `-v open-webui:/app/backend/data` in your Docker command. This step is crucial as it ensures your database is properly mounted and prevents any loss of data.

> [!TIP]  
> If you wish to utilize Open WebUI with Ollama included or CUDA acceleration, we recommend utilizing our official images tagged with either `:cuda` or `:ollama`. To enable CUDA, you must install the [Nvidia CUDA container toolkit](https://docs.nvidia.com/dgx/nvidia-container-runtime-upgrade/) on your Linux/WSL system.

### Installation with Default Configuration

- **If Ollama is on your computer**, use this command:

  ```bash
  docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

- **If Ollama is on a Different Server**, use this command:

  To connect to Ollama on another server, change the `OLLAMA_BASE_URL` to the server's URL:

  ```bash
  docker run -d -p 3000:8080 -e OLLAMA_BASE_URL=https://example.com -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

- **To run Open WebUI with Nvidia GPU support**, use this command:

  ```bash
  docker run -d -p 3000:8080 --gpus all --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:cuda
  ```

### Installation for OpenAI API Usage Only

- **If you're only using OpenAI API**, use this command:

  ```bash
  docker run -d -p 3000:8080 -e OPENAI_API_KEY=your_secret_key -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
  ```

### Installing Open WebUI with Bundled Ollama Support

This installation method uses a single container image that bundles Open WebUI with Ollama, allowing for a streamlined setup via a single command. Choose the appropriate command based on your hardware setup:

- **With GPU Support**:
  Utilize GPU resources by running the following command:

  ```bash
  docker run -d -p 3000:8080 --gpus=all -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
  ```

- **For CPU Only**:
  If you're not using a GPU, use this command instead:

  ```bash
  docker run -d -p 3000:8080 -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama
  ```

Both commands facilitate a built-in, hassle-free installation of both Open WebUI and Ollama, ensuring that you can get everything up and running swiftly.

After installation, you can access Open WebUI at [http://localhost:3000](http://localhost:3000). Enjoy! 😄

### Other Installation Methods

We offer various installation alternatives, including non-Docker native installation methods, Docker Compose, Kustomize, and Helm. Visit our [Open WebUI Documentation](https://docs.openwebui.com/getting-started/) or join our [Discord community](https://discord.gg/5rJgQTnV4s) for comprehensive guidance.

### Troubleshooting

Encountering connection issues? Our [Open WebUI Documentation](https://docs.openwebui.com/troubleshooting/) has got you covered. For further assistance and to join our vibrant community, visit the [Open WebUI Discord](https://discord.gg/5rJgQTnV4s).

#### Open WebUI: Server Connection Error

If you're experiencing connection issues, it’s often due to the WebUI docker container not being able to reach the Ollama server at 127.0.0.1:11434 (host.docker.internal:11434) inside the container . Use the `--network=host` flag in your docker command to resolve this. Note that the port changes from 3000 to 8080, resulting in the link: `http://localhost:8080`.

**Example Docker Command**:

```bash
docker run -d --network=host -v open-webui:/app/backend/data -e OLLAMA_BASE_URL=http://127.0.0.1:11434 --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```

### Keeping Your Docker Installation Up-to-Date

Check our Updating Guide available in our [Open WebUI Documentation](https://docs.openwebui.com/getting-started/updating).

### Using the Dev Branch 🌙

> [!WARNING]
> The `:dev` branch contains the latest unstable features and changes. Use it at your own risk as it may have bugs or incomplete features.

If you want to try out the latest bleeding-edge features and are okay with occasional instability, you can use the `:dev` tag like this:

```bash
docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui --add-host=host.docker.internal:host-gateway --restart always ghcr.io/open-webui/open-webui:dev
```

### Offline Mode

If you are running Open WebUI in an offline environment, you can set the `HF_HUB_OFFLINE` environment variable to `1` to prevent attempts to download models from the internet.

```bash
export HF_HUB_OFFLINE=1
```

## What's Next? 🌟

Discover upcoming features on our roadmap in the [Open WebUI Documentation](https://docs.openwebui.com/roadmap/).

## License 📜

This project contains code under multiple licenses. The current codebase includes components licensed under the Open WebUI License with an additional requirement to preserve the "Open WebUI" branding, as well as prior contributions under their respective original licenses. For a detailed record of license changes and the applicable terms for each section of the code, please refer to [LICENSE_HISTORY](./LICENSE_HISTORY). For complete and updated licensing details, please see the [LICENSE](./LICENSE) and [LICENSE_HISTORY](./LICENSE_HISTORY) files.

## Support 💬

If you have any questions, suggestions, or need assistance, please open an issue or join our
[Open WebUI Discord community](https://discord.gg/5rJgQTnV4s) to connect with us! 🤝

## Star History

<a href="https://star-history.com/#open-webui/open-webui&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=open-webui/open-webui&type=Date" />
  </picture>
</a>

---

Created by [Timothy Jaeryang Baek](https://github.com/tjbck) - Let's make Open WebUI even more amazing together! 💪
