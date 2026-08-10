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
