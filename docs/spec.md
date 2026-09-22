# Specification: Docker Nginx App Launcher PoC

## 1. Goal

Provide a reproducible local proof of concept in which several FastAPI web
applications run in Docker, Nginx is the only public entry point, and a
Launcher screen manages application registration and lifecycle operations.

The project is for learning and local verification. It is not a production
deployment system.

## 2. Scope

### In scope

- Nginx path routing through `http://localhost:8080`.
- A Launcher UI at `/launcher/`.
- Host-side Manager API on `127.0.0.1:9000`.
- Persisted dynamic application registry in `config/apps.json`.
- Generate Compose and Nginx configuration from the registry.
- Add, edit, delete, open, start, stop, restart, rebuild, and log operations.
- Safe optional deletion of source directories below `apps/`.
- Folder-tree source selection rooted at the project and `apps/`.
- Docker image/container explanation panel on every sample application page.
- Windows batch and POSIX shell operation scripts.
- Validated multi-service Compose bundles for applications that need a web
  frontend, API, background worker, Redis, or PostgreSQL.
- YouTube-provided transcript retrieval with audio/STT fallback and source
  metadata in the YouTube Transcripter application.
- Detailed key-point extraction from the effective transcript with selectable
  LLM and editable prompt.

### Out of scope

- Production authentication and authorization.
- HTTPS, Internet exposure, cloud deployment, Kubernetes, database, and
  multi-user tenancy.
- Docker socket access from a container.

## 3. Functional requirements

### FR-001: Single public entry

Only Nginx publishes host port `8080`. Launcher and all application services
must expose only their internal ports on the Docker network.

### FR-002: Sample application contract

Every app source folder contains a Dockerfile, requirements file, and FastAPI
source. Each running app provides:

| Endpoint | Required behavior |
| --- | --- |
| `GET /` | HTML page with an app test button and Docker learning panel |
| `GET /health` | JSON health result |
| `GET /api/test` | JSON success message |

Browser API calls must use relative paths to work below Nginx route prefixes.

### FR-003: Launcher

The Launcher must list registered applications and show the display name,
status, public URL, and source directory. It must provide Open, Start, Stop,
Restart, Rebuild, Logs, Edit, and Delete controls.

Open must use the record's `route_path`, not its `app_id`.

### FR-004: Registration fields

| Field | Meaning | Constraints |
| --- | --- | --- |
| `display_name` | human-facing GUI label | 1–120 characters |
| `app_id` | immutable service and management identifier | lower-case letters, digits, hyphens; 1–63 characters |
| `source_directory` | project-relative app source folder | inside project and contains the selected Dockerfile |
| `route_path` | public Nginx path | absolute, no traversal, normalized with trailing slash |
| `internal_port` | app port in Docker network | 1–65535 |
| `health_path` | app health URL inside container | safe absolute path |
| `dockerfile` | Dockerfile relative to source folder | cannot escape source folder |

The values may differ. Example: `app_id=app4-revive`,
`source_directory=apps/app4`, and `route_path=/app4/` is valid.

### FR-005: Source selection

The management form starts with `apps` as its source value. The folder dialog
lists `.` (project folder), `apps`, and safe subdirectories. It writes only a
relative folder path to the form and never uploads files. A final registration
is accepted only when its selected source directory contains the Dockerfile.

### FR-006: Manager API

Manager API validates records, persists them atomically, and exposes controlled
CRUD and lifecycle endpoints. It must not execute arbitrary request-supplied
commands.

### FR-007: Generated artifacts

The Manager API generates, and owns, these files:

- `generated/docker-compose.apps.yml`
- `generated/nginx.conf`

They are derived artifacts; manual edits are overwritten. They contain all
enabled registry entries.

### FR-008: Route refresh

After add, edit, delete, or explicit generation, Manager API recreates Nginx.
Generated Nginx configuration resolves app service names dynamically, so Nginx
can start when a newly registered app is not yet running. A stopped app may
return a gateway error until started, but the route must not disappear as 404.

### FR-009: Lifecycle actions

| Action | Required effect |
| --- | --- |
| Start | `docker compose up -d --build <app_id>`; creates first container too |
| Stop | stop only; preserve registry, image, and source |
| Restart | restart the current container/image |
| Rebuild | rebuild image; user then starts/restarts it |
| Delete | remove registry/service; source removal is separately confirmed |

### FR-010: Safe deletion

Source deletion is opt-in. The Manager API must reject project root, `apps`
root, paths outside the project, symlinks, and non-directory values.

### FR-011: Docker learning panel

Every sample app page explains, in Japanese:

- Docker image: Python 3.12-slim base, installed FastAPI/Uvicorn dependencies,
  app source, and Uvicorn command.
- Docker container: running instance of that image, separate process/runtime
  memory, and internal port 8000 endpoint used by Nginx.
- Rebuild changes an image; Start and Restart operate on containers.

### FR-012: Validated Compose bundles

A registration may declare either a single-service application or a
multi-service Compose bundle. A bundle stores its project-relative source
directory, its Compose file, its public service name, and that service's
internal port. The Manager API must read and validate the bundle file before
generation; it must never execute an arbitrary request-provided command or
unvalidated external Compose file.

Bundle validation must reject host port mappings, host networking, privileged
containers, Docker socket mounts, bind mounts outside the bundle source, and
build contexts or Dockerfiles that escape the bundle source. Generated service
names must be prefixed with the registration's `app_id`, so independent bundles
cannot collide. Only the selected public service is routed by Nginx; supporting
services remain internal on `multiapp_net`.

Named PostgreSQL and Redis volumes are permitted and must remain after Stop,
Restart, or Rebuild. Delete removes the generated bundle services but preserves
named volumes by default. No secret value is stored in the Launcher registry or
submitted through the browser UI.

For a browser-facing bundle, static assets and browser API calls must remain
below the registration route prefix, and internal service references must use
the generated namespaced Compose service names.

For a bundle whose public service is a browser application, the application must
be aware of its registered route prefix. Its static assets and browser API calls
must remain below that prefix, and the generated bundle service references must
use the namespaced Compose service names. This keeps a frontend mounted at a
route such as `/youtube/` styled and connected to its internal FastAPI service.

### FR-013: External persistent database

The YouTube Transcripter database may be operated by a separate database
Compose project rather than by the Launcher-generated bundle. The database
project owns the explicitly named stable volume `youtube-transcripter-db-data`
and joins the application network using the
stable service name `youtube-db`. It must not publish a host port. Launcher API,
worker, and migration services use the same external database URL, and stopping
or rebuilding the Launcher stack must not remove the database volume.

Database migration must use a dump-and-restore workflow with a verified backup
and a rollback path. The old database volume remains untouched until the new
database has passed schema, data, API health, and GUI verification.

### FR-014: Celery worker availability

The YouTube worker must listen to the `transcription` and `correction` queues,
restart automatically when it exits, and expose a container healthcheck based on
Celery ping. The YouTube API must check for an active worker before accepting a
transcription job. If no worker responds, it must return HTTP 503 and mark the
created job as failed with an actionable recovery message instead of silently
leaving it pending.

### FR-015: Selectable proofreading and QA model

Proofreading and transcript QA must support `gpt-4o-mini`, `gpt-4o`, and
`gpt-5-mini`. The default remains `gpt-4o-mini` for cost control. The
transcription model selection is independent and must not include `gpt-5-mini`.

### FR-016: Two-stage YouTube transcript retrieval

For each submitted YouTube video, the worker must first inspect the
YouTube-provided transcript tracks before downloading audio. Manually created
tracks take precedence over auto-generated tracks. When multiple languages are
available, prefer the requested application language, then Japanese, then
English, then another available language within the selected track type.

If a usable YouTube transcript is found, store it as the effective transcript
and do not run audio extraction, preprocessing, or STT. If no usable track is
available, or retrieval fails because of an unavailable/private video,
network/library error, or malformed URL, record the retrieval outcome and run
the existing audio transcription path. If both paths fail, return a clear
complete-transcription failure without exposing a raw traceback in the UI.

The stored YouTube transcript must retain its video ID, language, manual vs
auto-generated flag, available track summary, and timestamped segments when
provided. The existing audio transcript remains distinguishable by source.

### FR-017: Detailed key-point extraction

The Results page must provide a `Key Points` tab immediately to the right of
`Proofread`. The tab must offer an LLM selector, an asynchronous key-point
extraction action, and a prompt-edit action. The prompt editor starts with the
specified detailed Japanese prompt, and the user may edit it before execution.

The effective transcript, including a YouTube-provided transcript when
available, is the only source text supplied to the extraction task. The
selected model, edited prompt, result text, and creation time must be retained
for the job. Failed extraction must show a clear error and must not erase the
existing Transcript or Proofread result. Allowed models are `gpt-4o-mini`,
`gpt-4o`, and `gpt-5-mini`; the default is `gpt-4o-mini`.

### FR-018: Re-run failed transcription jobs

When a user opens a failed job in Results and selects `Re-run`, the frontend
must submit the original YouTube URL and language with the selected
transcription model to create a new job. The request must pass through the
routed API proxy without a trailing-slash redirect that changes the POST
endpoint. The button must show an in-progress state, switch Results to the new
job ID after success, and show an actionable error when submission fails.

### FR-019: Editable and highlighted result tabs

The YouTube Transcript, Transcript, Proofread, Key Points, Q&A, and Note tabs
must display their textual content in an inline editor by default. A user may
insert, delete, and replace text and may apply bold or yellow highlighting to a
selected range without switching to a separate viewer. The formatting must be
visible immediately in the editor and survive refresh.

The API must persist edits only for documented result content types and must
reject unknown content types or missing Q&A identifiers. Existing
`**...**` and `==...==` formatting remains supported. Formatting markers must
not be sent as semantic transcript text to export or LLM processing.

### FR-021: Preserve the last Library folder

When a user opens a Library item, edits its result, and returns to Library,
the Library must restore the folder that was selected immediately before the
item was opened. If that folder no longer exists, the UI may fall back to the
first available folder.

### FR-022: Automatic proofreading after transcription

Every successful Transcript execution must automatically enqueue Proofread
using the selected proofreading model. Proofread is not an optional step and
must not require a separate user action. The Results page must remove the
Proofread tab; while automatic Proofread is running, the Transcript tab may
show the raw transcript, then must show the generated Proofread text when it
becomes available. Existing editable and export behavior must continue to
target the available corrected text.

### FR-023: Stable Library folder ordering

The Library folder tree must always display the folder named `Inbox` first
among its siblings. All other folders must appear after `Inbox` in a stable
name/path order.

### FR-024: Default title for transcribed YouTube jobs

When the user does not provide a title, a completed Transcript job must have
an initial title in the form `【配信者名】YouTube YYYY/M/D`. The date is written
without zero-padding, and the generated title must be stored on both the Job
and its Library Item. A user-provided title must never be replaced by the
generated title. If YouTube metadata does not provide a channel/uploader name,
the fallback name `YouTube` is used.

### FR-020: Selective all-services startup

`run50_start_all.bat` and `run50_start_all.sh` must retain their current
full-start behavior when called without arguments, and must accept documented
options for skipping already-satisfied checks or avoiding an unnecessary image
build. The `--quick` option skips the Docker file check, external database
start, status display, and image build while still starting the Manager API,
Docker services, and worker health check. Individual options must include
`--skip-init`, `--skip-manager`, `--skip-database`, `--no-build`,
`--skip-status`, and `--skip-worker-check`.

When `run50` explicitly starts the database, it must pass the corresponding
skip option to `run32_docker_start_detached` so the database start is not
duplicated. `run32` must continue to start the database by default when run
directly.

## 4. External interfaces

### Browser paths

| Path | Destination |
| --- | --- |
| `/launcher/` | Launcher |
| `/app1/` | sample app 1 |
| dynamic `route_path` such as `/app4/`, `/app5/` | registered app |

### Manager API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | availability |
| GET | `/api/apps` | registry list |
| GET | `/api/directories` | folder-tree values |
| POST | `/api/apps` | register app |
| PATCH | `/api/apps/{app_id}` | edit app |
| DELETE | `/api/apps/{app_id}` | delete app |
| POST | `/api/apps/{app_id}/start` | create/build/start |
| POST | `/api/apps/{app_id}/stop` | stop |
| POST | `/api/apps/{app_id}/restart` | restart |
| POST | `/api/apps/{app_id}/rebuild` | rebuild image |
| GET | `/api/apps/{app_id}/logs` | bounded logs |
| POST | `/api/generate` | regenerate artifacts and refresh Nginx |

The YouTube job result response includes `youtube_transcript` with retrieval
status (`available`, `unavailable`, or `error`), selected language/source
metadata, available tracks, text, and segments. The existing `transcript`
field remains the effective transcript consumed by downstream processing.

## 5. Success criteria

1. `scripts/run50_start_all.bat` starts Manager API and Docker services.
2. Launcher opens at `http://localhost:8080/launcher/`.
3. Every enabled application route reaches Nginx, and started apps return 200.
4. New registration produces the two generated artifacts and a public route.
5. First Start works for a newly registered app without a pre-existing
   container.
6. Add, Start, Stop, Delete-preserve-source, and Delete-source flows pass
   automated and runtime verification.
7. `python -m pytest -q` passes.
8. The Docker stop script stops and removes every Compose service defined by
   both the base and generated Compose files, including registered apps.
9. A validated multi-service bundle can be registered, started, routed only
   through Nginx, stopped, and started again while retaining its named database
   volume.
10. YouTube jobs use a YouTube-provided transcript without audio/STT when one
    is usable, otherwise automatically use the existing audio fallback; the
    Results page shows YouTube Transcript immediately before Transcript.
11. A completed job exposes Key Points immediately to the right of Proofread;
    the user can select an allowed LLM, edit the default detailed prompt,
    execute asynchronously, and view the saved extraction without changing
    the Transcript or Proofread result.
12. Re-running a failed Results job creates and opens a new job using the
    original video URL/language and selected model; the UI indicates progress
    and surfaces submission failures.
13. Textual content in every Results tab can be edited and highlighted inline,
    is persisted, and remains safely rendered after reload.
14. All-services startup supports documented selective options while the
    no-argument command remains backward compatible.
