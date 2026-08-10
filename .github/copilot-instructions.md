# Copilot Instructions: Docker Nginx App Launcher PoC

## Purpose and source of truth

This repository is a beginner-friendly Spec-Driven Development (SDD) proof of
concept. It runs multiple FastAPI applications behind one Nginx entry point and
manages dynamically registered applications from a Launcher UI.

Before any implementation work, read these documents in order:

1. `docs/spec.md`
2. `docs/architecture.md`
3. `docs/task.md`

Treat them as the source of truth. If a user request changes behavior,
architecture, security boundaries, routes, or operations, update the matching
SDD document and task before writing implementation code.

## Required SDD workflow

1. Inspect the current configuration, source, and generated artifacts.
2. Add or update a numbered requirement in `docs/spec.md`.
3. Add a pending task in `docs/task.md`.
4. Update `docs/architecture.md` when components, data flow, network flow, or
   generated artifacts change.
5. Implement the smallest clear change.
6. Add or update automated tests for backend behavior.
7. Run focused tests and required runtime checks.
8. Mark the task complete only after verification succeeds.
9. Report changed files, commands run, results, and known limitations.

Never delete completed tasks; they are project history. Do not overwrite
unrelated worktree changes.

## Architecture invariants

- Nginx is the only Docker service that publishes a host port: `8080:80`.
- Launcher and application services use Docker internal networking only.
- Never expose application ports to the host and never use container IPs.
- Nginx routes public paths to Compose service names.
- Launcher never runs Docker commands and never imports Docker SDK.
- Never mount `/var/run/docker.sock` into Launcher.
- The host-side Manager API is the only component allowed to run controlled
  Docker Compose commands.
- Docker commands must be argument arrays with a fixed Compose file set; never
  accept a request-provided shell command or image name.
- Source deletion is allowed only below `apps/`, never for the project root,
  symlinks, or arbitrary paths.

## Current component contract

| Component | Responsibility | Public access |
| --- | --- | --- |
| Nginx | sole entry point and path reverse proxy | `localhost:8080` |
| Launcher | list, open, register, edit, delete, and lifecycle UI | `/launcher/` through Nginx |
| Manager API | registry persistence, config generation, Docker lifecycle | host loopback `127.0.0.1:9000` |
| App service | FastAPI sample app with UI, health, and test API | Nginx path only |

## Dynamic registration rules

An application record in `config/apps.json` has separate values:

- `display_name`: human-facing label.
- `app_id`: immutable lower-case Compose service identifier.
- `source_directory`: project-relative source folder with Dockerfile.
- `route_path`: public Nginx URL, always ending in `/`.
- `internal_port`, `health_path`, `dockerfile`, `enabled`, `description`.

`app_id`, source folder name, and route path do not need to match. Open links
must use `route_path`, not `app_id`. For example, `app_id=app4-revive` may use
`source_directory=apps/app4` and `route_path=/app4/`.

Manager API atomically writes the registry and generates these derived files:

- `generated/docker-compose.apps.yml`
- `generated/nginx.conf`

Do not edit generated files by hand. Registration changes must regenerate them
and recreate Nginx. Generated Nginx routes use Docker DNS at request time so
Nginx remains startable while a newly registered app is stopped.

## Lifecycle rules

- **Start**: `docker compose ... up -d --build <app_id>`; this creates and
  starts an app that has never existed before.
- **Stop**: stops its existing container and preserves image/source/registry.
- **Restart**: restarts the existing container with the same image.
- **Rebuild**: rebuilds the image; follow it with Start or Restart to run it.
- **Delete**: removes registration and Compose service. Source deletion is
  separately confirmed and opt-in.

When app containers are rebuilt or recreated outside Manager API, recreate
Nginx as well to avoid stale upstream addresses.

## Application implementation rules

Each sample application provides:

- `GET /` HTML page
- `GET /health` JSON health response
- `GET /api/test` JSON success response

Use relative browser requests such as `./api/test`, because the app is served
below an Nginx path. Each application page must explain, in Japanese, what its
Docker image contains and what its running Docker container represents.

Keep code beginner-readable. Add a purpose comment before each major function
or block. Use aligned inline comments where comments are needed; do not use a
framework beyond FastAPI, Uvicorn, Docker Compose, Nginx, and plain HTML.

## Reproducible verification

Use Windows `.bat` scripts or their `.sh` counterparts where applicable:

- `scripts/run50_start_all.*`: start Manager API and Docker stack.
- `scripts/run35_docker_status.*`: verify service status.
- `scripts/run40_nginx_check.*`: verify Nginx configuration/routes.
- `scripts/run41_app_health_check.*`: verify app health endpoints.
- `scripts/run42_manager_check.*`: verify Manager API.
- `scripts/run51_stop_all.*`: stop the stack.

At minimum, run `python -m pytest -q` after Python changes. For registration
or route changes, verify add, initial Start, Stop, and Nginx access of the new
route. Do not claim runtime verification unless Docker Desktop and Manager API
are actually running.
