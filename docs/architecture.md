# Architecture: Docker Nginx App Launcher PoC

## 1. System overview

```text
Browser
  │ http://localhost:8080
  ▼
Nginx container ── Docker network ── Launcher container
  │                                  │
  ├── dynamic app services            └── HTTP only
  │    app1, app2, app3, ...              host.docker.internal:9000
  │
  └── service-name routing                 ▼
                                           Manager API (host process)
                                                │
                                                ├── config/apps.json
                                                ├── generated/*.yml, *.conf
                                                └── controlled Docker Compose
```

Nginx is the only publicly exposed container. Manager API runs on the host and
is bound to `127.0.0.1:9000`; it is not routed through Nginx.

Browser bundles are built with their registered public base path (for example,
`/youtube`). Nginx strips that prefix for the frontend page and static assets,
but preserves it for the frontend's `/api-proxy/` location so Next.js can apply
its base-path rewrite. The generated API service URL is supplied both at
frontend build time and runtime. Single-service apps continue to receive the
legacy prefix-stripped request. The
bundle generator also rewrites internal URL hostnames such as `api`, `redis`,
and `postgres` to their generated `<app_id>-<service>` names.

The YouTube frontend keeps `trailingSlash` enabled for its routed page URLs but
skips Next.js automatic trailing-slash redirects. This is required for REST
POST requests such as Re-run: redirecting `/api/jobs/transcribe` before the
API rewrite can change the request URL and prevent the new job from being
created.

Results text editing uses a shared browser `contenteditable` component. The
component renders the existing lightweight `**...**` and `==...==` format,
allows text insertion/deletion and inline formatting, and serializes the safe
subset back to those markers. It accepts plain-text paste to avoid storing
untrusted HTML. The backend stores the marker text in the existing Text
columns; a controlled result-content endpoint validates the target content
type and record ownership before updating it. Formatting markers are removed
when transcript text is exported or supplied to LLM/QA processing.

The Library page keeps the selected folder in the page-level navigation state,
so opening an item and returning from Results restores the folder that was
active before the item was opened. Successful transcription tasks enqueue the
Proofread task automatically with the requested proofreading model. Results
does not expose a separate Proofread tab; its Transcript tab shows the raw
transcript until the automatic correction is available, then shows the
corrected text.

Folder-tree responses explicitly sort each sibling group with `Inbox` first,
then sort the remaining folders by normalized name and path. During
transcription, the worker reads YouTube metadata before choosing the subtitle
or audio path. If no user title exists, it stores
`【uploader】YouTube YYYY/M/D` on the Job and corresponding Library Item; a
metadata failure falls back to `【YouTube】YouTube YYYY/M/D`.

## 2. Components

### 2.1 Nginx

- Image: `nginx:1.27-alpine`.
- Host mapping: `8080:80` only.
- Mounts `generated/nginx.conf` read-only as its active virtual host.
- Routes `/launcher/` to `launcher:8000`.
- Routes each registered `route_path` to its registered Compose service.
- Uses Docker DNS resolver `127.0.0.11` and request-time upstream variables for
  generated app routes. This prevents Nginx startup failure when a just-added
  service has not been started yet.

### 2.2 Launcher

- FastAPI process in a Docker container, internal port `8000`.
- Calls the host Manager API through `host.docker.internal:9000`.
- Offers legacy app list/status actions and dynamic management page.
- Applies Basic authentication to management endpoints.
- Does not access Docker Engine, local files, or the Docker socket.

### 2.3 Manager API

- FastAPI process started on the Windows host by `scripts/run20_manager_start`.
- Owns registry validation, persistence, Compose/Nginx generation, lifecycle
  command execution, and source deletion safeguards.
- Invokes only this Compose shape:

```text
docker compose -f docker-compose.yml -f generated/docker-compose.apps.yml <fixed arguments>
```

- Recreates Nginx after configuration generation to activate route changes.

### 2.4 Application services

- Source folders: `apps/<folder>/`.
- Each Dockerfile starts from `python:3.12-slim`, installs requirements, copies
  `src`, and runs Uvicorn on port `8000`.
- Services are dynamically named by `app_id`, not source folder name.
- Each page includes a Docker learning panel that distinguishes image from
  container.

### 2.5 Validated Compose bundles

A bundle is one Launcher registration containing several generated services.
For example, a transcription app can contain a browser-facing Next.js frontend,
an internal API, PostgreSQL with a named data volume, Redis, a one-shot schema
migration, and a Celery worker. Nginx routes only to the bundle's declared
public service; all other services use Compose service names on `multiapp_net`.

Manager API parses the source Compose file as data and generates a normalized
entry in `generated/docker-compose.apps.yml`. It validates the permitted
Compose subset, prefixes every generated service and named volume with the
registration `app_id`, removes all host port publication, and rejects unsafe
features such as host networking, privileged mode, Docker socket mounts, or
paths that escape the bundle source. This preserves the existing security
boundary: Launcher still communicates only by HTTP and Nginx remains the sole
host-port publisher.

### 2.6 External persistent database

The YouTube Transcripter PostgreSQL service is operated by
`database/docker-compose.yml`, independently from the generated application
Compose file. It owns the stable named volume `youtube-transcripter-db-data`
and joins the stable Docker network `youtube_transcripter_net` with the alias
`youtube-db`. PostgreSQL has no host port mapping. The Launcher API, worker, and
Alembic migration service connect to `youtube-db:5432`.

The database stack is started before the Launcher stack and stopped separately.
Neither `docker compose down` for the Launcher nor application deletion removes
the database volume. Backups are created with `pg_dump` before migration and
before any destructive maintenance operation. The supported operations are
`run25_database_start`, `run26_database_stop`, `run27_database_status`,
`run28_database_backup`, and the confirmation-gated `run29_database_restore`
scripts. The Compose volume name is explicitly fixed as
`youtube-transcripter-db-data`, independent of the Compose project name.

The YouTube worker is explicitly routed to the `transcription` and
`correction` queues, uses `restart: unless-stopped`, and has a Celery ping
healthcheck. The API performs a worker ping before publishing a transcription
task, so a missing worker produces a visible 503 error rather than a successful
request followed by an indefinitely pending job. `run43_youtube_worker_check`
is called by the all-services startup script and waits for the routed health
endpoint to report at least one worker.

Proofreading and QA use the same OpenAI chat client and allow
`gpt-4o-mini`, `gpt-4o`, or `gpt-5-mini`. The UI defaults to `gpt-4o-mini`;
when `gpt-5-mini` is selected, requests omit the sampling-temperature option
so the reasoning model receives only supported parameters.

Key-point extraction uses the same Celery worker and OpenAI chat client as
proofreading and QA. The API validates the selected model, accepts an edited
prompt, and queues a dedicated extraction task. The result is stored in a
one-to-one `key_points_summaries` record containing the prompt, model, output,
and timestamp; it does not replace `transcripts` or `corrected_transcripts`.
The Results UI places `Key Points` immediately to the right of `Proofread` and
provides model selection, execution, and prompt editing controls.

### 2.7 Two-stage YouTube transcript retrieval

The YouTube worker checks `youtube-transcript-api` before creating an audio
extraction job. It normalizes the selected track into text and timestamped
segments, preferring manual tracks and then the requested language, Japanese,
English, or another available language. The result is stored in the dedicated
`youtube_transcripts` record, including retrieval status and available-track
metadata.

When retrieval succeeds, the same text is saved as the effective `Transcript`
with `source=youtube`; audio extraction, preprocessing, and OpenAI STT are
skipped. When retrieval is unavailable or errors, the worker records that
outcome and executes the existing audio/STT path, saving its effective
`Transcript` with `source=audio`. Downstream correction, proofreading, QA, and
export continue to read the effective `Transcript` field.

The Results API returns both the effective transcript and the independent
YouTube transcript result. The frontend displays a `YouTube Transcript` tab
immediately before the existing `Transcript` tab. A missing YouTube transcript
is presented as an unavailable source, not as an application error when audio
fallback succeeds.

### 2.8 Detailed key-point extraction flow

```text
Results / Key Points
  ├─ select LLM and edit prompt
  └─ POST /api/jobs/{job_id}/key-points
          ↓
      Celery key_points_task
          ↓ reads effective Transcript only
      OpenAI chat completion
          ↓
      key_points_summaries row
          ↓
      GET /api/jobs/{job_id}/result
```

The default prompt requests chapter-based, detailed points, preserving claims,
background, evidence, examples, names, numbers, causality, comparisons,
conclusions, and speaker-attribution language. The worker omits the
temperature option for `gpt-5-mini`, matching the existing reasoning-model
handling. A task failure is reported in the job response/UI while preserving
all existing transcript and proofreading data.

## 3. Registry and generation flow

```text
Launcher management form
  │ validated HTTP request
  ▼
Manager API
  │ validate app_id, route, Dockerfile, source path, uniqueness
  ▼
config/apps.json  (atomic replace)
  │
  ├── generated/docker-compose.apps.yml
  └── generated/nginx.conf
          │
          ▼
docker compose up -d --force-recreate nginx
```

`config/apps.json` is the source of truth for registered apps. Generated files
are deterministic outputs and must not be edited manually.

## 4. Lifecycle flow

### Start a newly registered application

```text
Launcher → Manager API → docker compose up -d --build <app_id>
                         → build image from source_directory
                         → create/run container on multiapp_net
Browser → Nginx → Docker DNS → app service:internal_port
```

`up -d --build` is required because `docker compose start` works only when a
container already exists.

### Rebuild and restart

```text
Rebuild: Manager API → docker compose build <app_id>
Restart: Manager API → docker compose restart <app_id>
```

If an app container is rebuilt or recreated, Nginx must be recreated afterwards
to avoid using stale container addresses. The operation scripts do this, and
Manager API does it whenever generation changes routes.

### Start a registered bundle

```text
Launcher → Manager API → validate bundle definition
                         → generate prefixed internal services
                         → docker compose up -d --build <bundle services>
Browser  → Nginx → declared public service
                       ├── API
                       ├── PostgreSQL named volume
                       ├── Redis
                       └── worker
```

Stopping a bundle stops all of its services but does not remove named volumes.
Deleting its registry entry removes the generated services and route; database
volume deletion is a separate, explicit future operation.

## 5. Network and security boundaries

| Boundary | Rule |
| --- | --- |
| Browser → Nginx | only public Docker port |
| Nginx → Launcher/apps | Compose service names on `multiapp_net` |
| Launcher → Manager API | controlled HTTP to host-side loopback service |
| Manager API → Docker | fixed Compose command arguments only |
| Launcher → Docker socket | forbidden |
| Source deletion | only real directories below `apps/` |

## 6. Identity mapping example

| Concept | Example | Meaning |
| --- | --- | --- |
| GUI name | `test` | label shown to users |
| app_id | `app4-revive` | Compose service and management target |
| source directory | `apps/app4` | Docker build context |
| route path | `/app4/` | browser URL |
| image | project-prefixed `app4-revive` image | reusable build output |
| container | project-prefixed `app4-revive-1` | running image instance |

The values intentionally may not match.

## 7. Reproduction prerequisites

- Docker Desktop running and accessible to the user.
- Python environment with FastAPI, HTTPX, Pydantic, Uvicorn, and Pytest.
- Windows: use `.bat` scripts; POSIX: use matching `.sh` scripts.
- Project directory writable, including `config/`, `generated/`, and `.run/`.

## 8. Operational recovery

The Docker start and stop scripts use the same Compose-file pair:
`docker-compose.yml` and `generated/docker-compose.apps.yml`. This ensures a
shutdown removes Nginx, Launcher, and every registered application service.

| Symptom | Likely cause | Recovery |
| --- | --- | --- |
| 404 after app registration | Nginx has old generated config | `POST /api/generate` or recreate Nginx |
| Nginx fails with upstream host not found | static upstream resolution for stopped new service | use generated dynamic resolver config |
| Start fails for new app | container does not exist yet | use Start, which runs `up -d --build` |
| 502 after container recreation | Nginx has stale upstream connection/address | recreate Nginx |
| Open goes to wrong URL | app_id used as URL | use record's route_path |
| YouTube job remains pending | worker was stopped or unhealthy | check `/youtube/api-proxy/health/`, then run `docker compose ... up -d --build youtube-transcripter-worker` and retry |

## 9. Selective startup options

`run50_start_all.{bat,sh}` runs the complete startup sequence without
arguments. For an already initialized environment, `--quick` skips the Docker
file check, database start, status display, and image builds, while retaining
Manager API startup, service startup, and worker health verification.

The individual options are `--skip-init`, `--skip-manager`,
`--skip-database`, `--no-build`, `--skip-status`, and `--skip-worker-check`.
The database skip option is forwarded to `run32_docker_start_detached`; direct
invocation of `run32` still starts the database unless explicitly skipped.
