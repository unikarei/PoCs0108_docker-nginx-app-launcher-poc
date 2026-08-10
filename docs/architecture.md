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
