# Task List: Reproducible Docker Nginx App Launcher PoC

## Task rules

- `[ ]` means pending; `[x]` means verified complete.
- Implement in order unless a task explicitly depends on a later correction.
- Before marking complete, run its listed verification.
- Keep completed tasks as an audit trail.

## Phase 0: Prepare repository and SDD documents

### [x] Task 0.1 Create project layout

Create `.github/`, `docs/`, `apps/`, `launcher/`, `manager-api/`, `config/`,
`generated/`, `scripts/`, and `tests/`.

### [x] Task 0.2 Create detailed SDD documents

Create `.github/copilot-instructions.md`, `docs/spec.md`,
`docs/architecture.md`, and this task list before implementation.

Verification: documents describe current requirements, architecture, reproduction
steps, and verification conditions.

## Phase 1: Build sample applications

### [x] Task 1.1 Create app1–app4 source templates

Each app has `Dockerfile`, `requirements.txt`, and `src/main.py` with root,
health, and test endpoints.

### [x] Task 1.2 Make applications subpath-safe

Use relative browser API URLs such as `./api/test`.

### [x] Task 1.3 Add Docker learning panels

Display per-app explanations of Docker image contents, Docker container runtime
meaning, internal port 8000, and rebuild/start/restart behavior.

Verification: application root pages contain both “Dockerイメージ” and
“Dockerコンテナ” explanations.

## Phase 2: Create host-side Manager API

### [x] Task 2.1 Define validated registry model

Persist `display_name`, `app_id`, `source_directory`, `route_path`, port,
health path, Dockerfile, description, enabled state, and timestamps in
`config/apps.json`.

### [x] Task 2.2 Implement safe path and uniqueness validation

Reject unsafe paths, absent Dockerfiles, invalid IDs/routes, duplicate IDs, and
duplicate routes.

### [x] Task 2.3 Generate Compose and Nginx artifacts

Generate `generated/docker-compose.apps.yml` and `generated/nginx.conf` from
enabled records. Treat both as derived files.

### [x] Task 2.4 Implement CRUD and folder-tree API

Provide list, add, update, delete, inspect, and directory-list endpoints.

### [x] Task 2.5 Implement lifecycle and log API

Provide status, initial Start (`up -d --build`), Stop, Restart, Rebuild, and
bounded Logs. Never allow request-provided shell commands.

### [x] Task 2.6 Implement safe source deletion

Require matching confirmation ID; preserve source by default; permit recursive
deletion only for real directories below `apps/`.

### [x] Task 2.7 Refresh Nginx after generated configuration changes

Recreate Nginx after add, update, delete, or explicit generation. Use Docker
DNS at request time for generated app routes so stopped new services do not
prevent Nginx from starting.

Verification: unit test generated route and Nginx refresh call; add a new app,
then verify its route is present without manual Nginx editing.

## Phase 3: Create Launcher

### [x] Task 3.1 Implement basic Launcher page

List apps, statuses, Open, Start, Stop, and Delete controls.

### [x] Task 3.2 Proxy management API calls

Launcher communicates with host-side Manager API through HTTP only and never
calls Docker directly.

### [x] Task 3.3 Implement management page

Support add/edit/delete/lifecycle/log actions. Use distinct display name,
app_id, source directory, and route path fields.

### [x] Task 3.4 Implement source folder-tree dialog

Open a project-relative tree, select `apps` initially, and submit only the
selected relative folder path. Do not upload files.

### [x] Task 3.5 Add operational help

Add blue `?` help controls for field definitions and lifecycle action guidance.

### [x] Task 3.6 Fix Open route behavior

Generate Open links from `route_path`, never from `app_id`.

Verification: an app with different `app_id` and `route_path` opens at the
registered route.

## Phase 4: Compose, Nginx, and scripts

### [x] Task 4.1 Configure base Compose services

Define Nginx and Launcher, internal `multiapp_net`, Nginx port `8080:80`, and
read-only generated Nginx configuration mount.

### [x] Task 4.2 Add host-side Manager API scripts

Provide `run20_manager_start` and `run21_manager_stop` scripts using `.run/`
PID tracking.

### [x] Task 4.3 Add Docker and verification scripts

Provide numbered start/stop/status/Nginx/app-health/Manager checks in both
batch and shell forms.

### [x] Task 4.4 Recreate Nginx after app replacement

`run32_docker_start_detached` recreates Nginx after app recreation to prevent
stale upstream addresses and 502 errors.

## Phase 5: Automated tests

### [x] Task 5.1 Add Manager API tests

Test invalid app IDs, registration generation, route refresh, lifecycle command
allowlist, preserve-source deletion, safe source deletion, and unsafe root
rejection.

### [x] Task 5.2 Run regression suite

Verification command:

```text
python -m pytest -q
```

Expected current result: `11 passed` or more as tests are extended.

## Phase 6: End-to-end reproduction procedure

### [x] Task 6.1 Start the stack

Windows:

```text
scripts\run50_start_all.bat
```

POSIX:

```text
./scripts/run50_start_all.sh
```

### [x] Task 6.2 Verify services

Run:

```text
scripts\run35_docker_status.bat
scripts\run40_nginx_check.bat
scripts\run41_app_health_check.bat
scripts\run42_manager_check.bat
```

### [x] Task 6.3 Verify dynamic registration

1. Create `apps/<new-app>/` containing Dockerfile, requirements, and FastAPI
   source.
2. In `/launcher/manage`, select its folder, set a unique app ID and route.
3. Register it.
4. Click Start once; this builds and creates the container.
5. Open its `route_path` and verify `/health` returns HTTP 200.
6. Test Stop, Start, Rebuild, Restart, Delete-preserve, and Delete-source.

## Phase 7: Documentation maintenance

### [x] Task 7.1 Keep reproduction documentation current

Update all four SDD files whenever the implementation or operational behavior
changes.

### [x] Task 7.2 Stop generated application services

Make `run33_docker_stop` pass both Compose files to `docker compose down`, so
it stops and removes Nginx, Launcher, and every registered application service.

Verification: inspect the command in both batch and POSIX scripts, then run
`docker compose -f docker-compose.yml -f generated/docker-compose.apps.yml config --services`.

### [x] Task 7.3 Document executable code units

Add beginner-friendly module overviews and professional docstrings to the
classes and functions in the Manager API, Launcher, and sample application
source files without changing their runtime behavior.

Verification: compile the updated Python modules and run `python -m pytest -q`.

### [x] Task 7.4 Separate application management with tabs

Show the registration form and the registered-applications list as accessible
tabs on the management page. Keep all existing registration and lifecycle APIs
unchanged.

Verification: compile the Launcher module and confirm the management HTML
contains two tab buttons and their corresponding panels.

## Phase 8: Validated multi-service Compose bundles

### [x] Task 8.1 Define bundle registry and validation rules

Add a registration mode for a project-local Compose bundle with a Compose file,
public service, and public internal port. Validate its services, build paths,
volumes, network settings, and port mappings against FR-012.

Verification: unit tests accept a safe multi-service bundle fixture and reject
host ports, Docker socket mounts, privileged mode, host networking, and paths
outside the bundle source.

### [x] Task 8.2 Generate namespaced bundle services and routes

Finish and test the implemented generator: it must prefix every bundle service
and named volume with `app_id`, rewrite `depends_on` and named-volume
references, join services to `multiapp_net`, and route only `public_service`
through Nginx. The generated Compose file must retain a source-local `env_file`
reference without copying secret values into the registry.

Verification: unit tests inspect generated Compose and Nginx output for a
bundle fixture. They must find no host ports, find prefixed service and volume
names, and find the Nginx upstream for the public service.

### [x] Task 8.3 Extend bundle lifecycle operations

Finish and test the implemented lifecycle mapping. Start, Stop, Restart,
Rebuild, Logs, and Delete must target every generated service belonging to one
bundle. Stop and Delete must preserve named data volumes by default.

Verification: unit tests assert fixed Compose arguments for a bundle and verify
that Stop and Delete do not include volume deletion.

### [x] Task 8.4 Add bundle registration controls to Launcher

Allow the management UI to choose single-service or bundle registration and,
for bundles, collect only the safe bundle metadata. Never expose secret values
in the UI or registry.

Verification: Launcher compiles and bundle requests are forwarded unchanged to
the Manager API.

### [x] Task 8.5 Create the YouTube production bundle definition

Keep the existing development `docker-compose.yml` unchanged. Add
`docker-compose.launcher.yml` for Launcher use: no host port mappings, named
PostgreSQL and Redis volumes, production frontend image, and source-local
`.env` handling for secrets.

Verification: `docker compose -f apps/0106_YoutubeTranscripter/docker-compose.launcher.yml config --quiet` succeeds with a temporary validation-only OpenAI key.

### [x] Task 8.6 Register and generate the YouTube bundle

Register the bundle with `source_directory=apps/0106_YoutubeTranscripter`,
`compose_file=docker-compose.launcher.yml`, `public_service=frontend`, an
internal port of `3000`, and a unique public route. Confirm the Manager API
generates only internal service ports and the Nginx route points to the
namespaced frontend service.

Verification: inspect `generated/docker-compose.apps.yml` and
`generated/nginx.conf`; run `docker compose ... config --quiet`.

### [x] Task 8.7 Runtime verify the YouTube Transcripter bundle

Start the registered bundle, open its Nginx route, and verify the frontend,
API proxy, worker, and database health. Stop and start it again, then verify
the PostgreSQL named volume remains present. Do not delete volumes during this
flow.

The frontend must be built for `/youtube/`, load its CSS/JavaScript assets below
that route, and send API requests through the routed frontend proxy to the
namespaced FastAPI service.

Verification: Docker status, Nginx route response, API health through the
frontend proxy, worker log, and `docker volume inspect` all succeed.

## Phase 9: External persistent YouTube database

### [x] Task 9.1 Define the external database boundary

Add the external database requirement and stable network/volume contract to the
SDD. Keep PostgreSQL out of the generated Launcher bundle and do not publish a
database host port.

### [x] Task 9.2 Create the database Compose project and operations

Create `database/docker-compose.yml` plus safe start, stop, status, backup, and
restore operations. Stop must preserve the explicitly named database volume.
Backup writes PostgreSQL custom-format files without host-side text encoding,
and restore requires explicit confirmation.

### [x] Task 9.3 Migrate the YouTube database safely

Dump the old database and current database, restore the selected old dump into
the external database, run migrations, and retain both source backups and the
old volume for rollback.

### [x] Task 9.4 Switch and verify Launcher database connectivity

Point API, worker, and migration services at `youtube-db`, then verify existing
transcripts through the frontend, API health, worker health, backup restore
metadata, and persistence across Launcher stop/start.

## Phase 10: Celery worker availability

### [x] Task 10.1 Guarantee worker startup and recovery

Route the worker to both application queues, add automatic restart and a Celery
ping healthcheck, and make the all-services startup script fail clearly when
the worker does not become healthy.

### [x] Task 10.2 Prevent silent pending jobs

Check for an active Celery worker before publishing a transcription task. If no
worker responds, return HTTP 503, record an actionable failed job, and require
the user to retry after worker recovery.

Verification: generated Compose contains the worker command, restart policy,
and healthcheck; the routed API health reports worker count; Compose config is
valid; and the updated Python module compiles.

## Phase 11: Current proofreading and QA models

### [ ] Task 11.1 Add GPT-5 mini to proofreading and QA

Add `gpt-5-mini` to backend validation and the Settings/Results selectors for
proofreading and QA only. Preserve `gpt-4o-mini` as the default and omit
unsupported sampling parameters for GPT-5 mini.

Verification: compile the changed Python modules and run the frontend build.

## Phase 12: Two-stage YouTube transcript retrieval

### [ ] Task 12.1 Define the YouTube transcript data contract

Add SDD-backed storage for YouTube transcript retrieval status, selected track
metadata, available tracks, timestamps, and the source of the effective
transcript. Add the `youtube-transcript-api` dependency and an Alembic
migration without changing existing transcript consumers.

### [ ] Task 12.2 Implement YouTube-first worker flow

Extract a video ID, prefer manual tracks over auto-generated tracks, select a
language deterministically, and retrieve the transcript before audio
extraction. Skip audio/STT when retrieval succeeds; otherwise record
unavailable/error and run the existing audio fallback. Preserve clear final
errors when both paths fail.

### [ ] Task 12.3 Add result and Batch UI subtitle information

Expose the retrieval result through the job result API and show subtitle
availability/selection metadata in the Batch result preview. Add a
`YouTube Transcript` Results tab immediately before the existing `Transcript`
tab, while preserving export, correction, proofreading, QA, and note behavior.

### [ ] Task 12.4 Test the two-stage flow

Add mocked tests for manual, auto-generated, unavailable, retrieval-error,
YouTube-success-without-STT, both-methods-fail, effective-transcript
selection, API serialization, and Results tab ordering. Run the backend tests,
frontend type check, and frontend production build where the environment
permits.

## Phase 13: Detailed key-point extraction

### [x] Task 13.1 Define key-point extraction contract

Add the SDD requirement, default detailed Japanese prompt, API request/result
shape, and one-to-one database storage for the selected model, edited prompt,
result text, and timestamp. Preserve existing transcript and proofreading
records.

### [x] Task 13.2 Implement asynchronous extraction

Add model validation, a dedicated OpenAI extraction service, a Celery task, and
the controlled `POST /api/jobs/{job_id}/key-points` endpoint. Read the
effective Transcript as input, support `gpt-4o-mini`, `gpt-4o`, and
`gpt-5-mini`, and omit unsupported temperature options for `gpt-5-mini`.

### [x] Task 13.3 Add the Key Points Results tab

Place `Key Points` immediately to the right of `Proofread`. Provide an LLM
selector, execution button, prompt editor button, saved-result display, and
polling behavior consistent with Proofread. The prompt editor starts with the
specified detailed prompt.

### [x] Task 13.4 Verify extraction behavior

Add mocked tests for request validation, prompt editing, model forwarding,
effective-transcript input, GPT-5 mini request options, result persistence,
failure preservation, API serialization, and tab ordering. Run backend tests,
frontend type checking, and the production build where the environment
permits.

## Phase 14: Failed-job Re-run

### [x] Task 14.1 Fix routed Re-run submission

Prevent Next.js trailing-slash redirects from rewriting API POST requests,
show a busy state while Re-run is submitted, and switch Results to the newly
created job. Verify the routed POST reaches the API without redirect and that
the frontend production build succeeds.

## Phase 15: Editable and highlighted Results tabs

### [ ] Task 15.1 Add the result-content editing contract

Document the supported result content types, controlled update request, Q&A
identifier requirement, and preservation of existing formatting markers.

### [ ] Task 15.2 Implement persisted result editing

Add the validated result-content update endpoint, shared safe markup helpers,
and removal of formatting markers from transcript export and LLM/QA input.

### [ ] Task 15.3 Make every Results text area inline-editable

Use a shared `contenteditable` editor for YouTube Transcript, Transcript,
Proofread, Key Points, Q&A, and Note. Support insertion, deletion, bold, and
yellow highlighting in place, with explicit save state and refresh-safe
serialization.

### [ ] Task 15.4 Verify result editing

Test content-type validation, persistence for each supported target, Q&A ID
handling, markup safety, export/LLM plain-text behavior, and the frontend
production build.

## Phase 16: Selective all-services startup

### [ ] Task 16.1 Add startup option contract

Document backward-compatible full startup, `--quick`, individual skip options,
and the database handoff between `run50` and `run32`.

### [ ] Task 16.2 Implement selective startup for Windows and POSIX

Add argument parsing to `run50_start_all.{bat,sh}` and
`run32_docker_start_detached.{bat,sh}`. Avoid duplicate database startup and
allow an already-built environment to start without rebuilding images.

### [ ] Task 16.3 Verify startup options

Check help and argument behavior on both script variants, preserve no-argument
behavior, and run the repository's script/config checks where Docker is
available.

## Phase 17: Library navigation and automatic proofreading

### [x] Task 17.1 Preserve the last selected Library folder

Keep the selected Library folder in page-level navigation state and restore it
when returning from an opened item in Results. Fall back to the first available
folder only when the previous folder was deleted.

### [x] Task 17.2 Run Proofread automatically after Transcript

Accept the proofreading model with a transcription request, enqueue Proofread
after a successful Transcript task, and make the corrected result available
without a separate Proofread action. Remove the Results Proofread tab and show
the corrected text from the Transcript tab when it is ready.

### [x] Task 17.3 Verify navigation and automatic Proofread

Run focused backend tests for request forwarding and automatic task chaining,
frontend assertions for folder restoration and tab removal, and the frontend
production build.

## Phase 18: Library ordering and default titles

### [x] Task 18.1 Fix Library folder ordering

Return folder trees with `Inbox` first among siblings and all other folders in
a stable normalized name/path order.

### [x] Task 18.2 Generate default YouTube titles

Read uploader/channel metadata during Transcript processing and, when the user
did not provide a title, persist `【配信者名】YouTube YYYY/M/D` on the Job and
Library Item. Preserve explicit user titles and use `YouTube` as the metadata
fallback name.

### [x] Task 18.3 Verify ordering and title behavior

Run focused backend tests for folder ordering and title generation, build the
frontend, and verify the running API/frontend health endpoints.
