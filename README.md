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
│  ├─ start.bat
│  ├─ stop.bat
│  ├─ status.bat
│  ├─ manager_start.bat
│  ├─ manager_stop.bat
│  ├─ start.sh
│  ├─ stop.sh
│  ├─ status.sh
│  ├─ manager_start.sh
│  └─ manager_stop.sh
└─ docker-compose.yml
```

## How to start Manager API

Windows:

```bat
scripts\manager_start.bat
```

Linux/macOS:

```bash
bash scripts/manager_start.sh
```

Health check:

```text
http://127.0.0.1:9000/health
```

## How to start Docker services

Windows:

```bat
scripts\start.bat
```

Linux/macOS:

```bash
bash scripts/start.sh
```

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
scripts\stop.bat
scripts\manager_stop.bat
```

Linux/macOS:

```bash
bash scripts/stop.sh
bash scripts/manager_stop.sh
```

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
