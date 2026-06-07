# Docker + Nginx Multi-App Launcher PoC

## Project purpose

This repository is a Spec-Driven Development (SDD) PoC that verifies the following architecture:

- Multiple web apps run in Docker containers.
- Nginx is the single host-side entry point.
- Apps are accessed by path routing (`/launcher`, `/app1`, `/app2`, `/app3`, `/app4`).
- Launcher controls app status, start, and stop through Manager API.
- Launcher does not access Docker directly.

## Architecture summary

```text
Browser
	-> Nginx (host port 8080)
	-> launcher / app1 / app2 / app3 / app4 (Docker internal network)

Launcher -> Manager API (host-side, 127.0.0.1:9000)
Manager API -> docker compose start/stop/ps (controlled commands only)
```

## Folder structure

```text
.
├─ .github/
│  └─ workflows/
│     └─ ci.yml
├─ apps/
│  ├─ app1/
│  ├─ app2/
│  ├─ app3/
│  └─ app4/
├─ docs/
├─ launcher/
├─ manager-api/
├─ nginx/
│  ├─ nginx.conf
│  └─ nginx.prod.conf
├─ scripts/
│  ├─ run20_manager_start.bat
│  ├─ run21_manager_stop.bat
│  ├─ run30_docker_init.bat
│  ├─ run31_docker_start_dev.bat
│  ├─ run32_docker_start_detached.bat
│  ├─ run33_docker_stop.bat
│  ├─ run34_docker_log.bat
│  ├─ run35_docker_status.bat
│  ├─ run40_nginx_check.bat
│  ├─ run41_app_health_check.bat
│  ├─ run42_manager_check.bat
│  ├─ run50_start_all.bat
│  ├─ run51_stop_all.bat
│  ├─ start.bat
│  ├─ stop.bat
│  ├─ status.bat
│  ├─ manager_start.bat
│  ├─ manager_stop.bat
│  ├─ run20_manager_start.sh
│  ├─ run21_manager_stop.sh
│  ├─ run30_docker_init.sh
│  ├─ run31_docker_start_dev.sh
│  ├─ run32_docker_start_detached.sh
│  ├─ run33_docker_stop.sh
│  ├─ run34_docker_log.sh
│  ├─ run35_docker_status.sh
│  ├─ run40_nginx_check.sh
│  ├─ run41_app_health_check.sh
│  ├─ run42_manager_check.sh
│  ├─ run50_start_all.sh
│  ├─ run51_stop_all.sh
│  ├─ start.sh
│  ├─ stop.sh
│  ├─ status.sh
│  ├─ manager_start.sh
│  └─ manager_stop.sh
└─ docker-compose.yml
```

## Quick start

Windows:

```bat
scripts\run10_uv_venv.bat
scripts\run11_uv_sync.bat
scripts\run50_start_all.bat
```

Linux/macOS/WSL:

```bash
chmod +x scripts/*.sh
bash scripts/run10_uv_venv.sh
bash scripts/run11_uv_sync.sh
bash scripts/run50_start_all.sh
```

Browser:

```text
http://localhost:8080/launcher/
```

## How to start Manager API

Windows:

```bat
scripts\run20_manager_start.bat
```

Linux/macOS:

```bash
bash scripts/run20_manager_start.sh
```

Compatibility wrappers are also available:

- `scripts/manager_start.bat`
- `scripts/manager_start.sh`

Health check:

```text
http://127.0.0.1:9000/health
```

## How to start Docker services

Windows:

```bat
scripts\run50_start_all.bat
```

Linux/macOS:

```bash
bash scripts/run50_start_all.sh
```

Compatibility wrappers are also available:

- `scripts/start.bat`
- `scripts/start.sh`

## How to access Launcher

```text
http://localhost:8080/launcher/
```

Launcher Basic Auth defaults:

- username: `launcher`
- password: `launcher-pass`

You can override using environment variables in the launcher service:

- `LAUNCHER_BASIC_AUTH_USER`
- `LAUNCHER_BASIC_AUTH_PASSWORD`

## How to access each app

```text
http://localhost:8080/app1/
http://localhost:8080/app2/
http://localhost:8080/app3/
http://localhost:8080/app4/
```

## How to stop services

Windows:

```bat
scripts\run51_stop_all.bat
```

Linux/macOS:

```bash
bash scripts/run51_stop_all.sh
```

Compatibility wrappers are also available:

- `scripts/stop.bat`
- `scripts/stop.sh`
- `scripts/manager_stop.bat`
- `scripts/manager_stop.sh`

## How to run checks

Windows:

```bat
scripts\run35_docker_status.bat
scripts\run40_nginx_check.bat
scripts\run41_app_health_check.bat
scripts\run42_manager_check.bat
```

Linux/macOS:

```bash
bash scripts/run35_docker_status.sh
bash scripts/run40_nginx_check.sh
bash scripts/run41_app_health_check.sh
bash scripts/run42_manager_check.sh
```

Notes:

- `run40_nginx_check` checks `/launcher/` with Basic Auth.
- You can override credentials with `LAUNCHER_BASIC_AUTH_USER` and `LAUNCHER_BASIC_AUTH_PASSWORD`.

## Script roles

Primary run scripts:

- `run20_manager_start` and `run21_manager_stop`: start or stop the host-side Manager API.
- `run30_docker_init`: verify Docker and required project files before startup.
- `run31_docker_start_dev`: foreground compose startup for log-focused development.
- `run32_docker_start_detached`: detached compose startup for normal use.
- `run33_docker_stop`: stop compose services.
- `run34_docker_log`: show compose logs.
- `run35_docker_status`: show compose status.
- `run40_nginx_check`: verify Nginx routes, including auth-protected `/launcher/`.
- `run41_app_health_check`: verify `/health` endpoints for launcher and app1-app4.
- `run42_manager_check`: verify Manager API endpoints.
- `run50_start_all` and `run51_stop_all`: standard start and stop sequence for daily use.

Compatibility wrappers:

- `start.* -> run50_start_all.*`
- `stop.* -> run51_stop_all.*`
- `status.* -> run35_docker_status.*`
- `manager_start.* -> run20_manager_start.*`
- `manager_stop.* -> run21_manager_stop.*`

## Security note about Manager API

- Manager API should run on localhost only for this PoC.
- Launcher never mounts Docker socket.
- Manager API accepts only controlled app names and controlled docker compose commands.
- Arbitrary command execution is intentionally not supported.

## Future extension method

To add a new app (for example app5):

1. Add `apps/app5/` with `Dockerfile`, `requirements.txt`, and `src/main.py`.
2. Add `app5` to `docker-compose.yml`.
3. Add route `/app5/` to `nginx/nginx.conf` (and `nginx/nginx.prod.conf` if needed).
4. Add `app5` to Launcher app list.
5. Add `app5` to Manager API allowed app names.

## HTTPS note

`nginx/nginx.prod.conf` is provided as a production-oriented template with TLS listeners.
You need certificate files at:

- `/etc/nginx/certs/fullchain.pem`
- `/etc/nginx/certs/privkey.pem`
