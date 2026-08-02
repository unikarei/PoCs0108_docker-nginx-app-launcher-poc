# Architecture: Docker + Nginx Multiple Web App Test Project

## 1. Architecture Overview

This project uses Nginx as the only public entrance.

All applications run as Docker services.

Nginx forwards requests to each application through the Docker internal network.

The Launcher application provides a control GUI.

The Manager API receives controlled management requests from Launcher and performs start, stop, and status operations.

Overall architecture:

```text
Browser
  |
  | http://localhost:8080
  v
Nginx container
  |
  | Docker internal network
  |
  +--> launcher container
  |
  +--> app1 container
  |
  +--> app2 container
  |
  +--> app3 container
  |
  +--> app4 container
  |
  +--> manager-api container or host-side manager service
```

---

## 2. Main Design Decision

The key design decision is:

```text
Use Method B for start and stop operations.
```

This means:

- Launcher does not control Docker directly.
- Launcher does not mount Docker socket.
- Launcher calls Manager API.
- Manager API is responsible for executing controlled commands.

This is safer than mounting Docker socket into the Launcher.

---

## 3. Service List

### 3.1 nginx

Role:

- Public entrance
- Reverse proxy
- Path-based routing

Host port:

```text
8080:80
```

Routes:

```text
/launcher/  -> launcher:8000
/app1/      -> app1:8000
/app2/      -> app2:8000
/app3/      -> app3:8000
/app4/      -> app4:8000
```

### 3.2 launcher

Role:

- Management GUI
- App list screen
- Open app buttons
- Status display
- Start and stop request sender

The Launcher does not execute Docker commands.

It sends requests to Manager API.

### 3.3 app1

Role:

- Test app 1
- Provides GUI
- Provides API endpoint

Internal port:

```text
8000
```

### 3.4 app2

Role:

- Test app 2
- Provides GUI
- Provides API endpoint

Internal port:

```text
8000
```

### 3.5 app3

Role:

- Test app 3
- Provides GUI
- Provides API endpoint

Internal port:

```text
8000
```

### 3.6 manager-api

Role:

- Receives management requests
- Checks container status
- Starts app services
- Stops app services

The first PoC may implement Manager API in one of two patterns.

### 3.7 app4

Role:

- Test app 4
- Provides GUI
- Provides API endpoint

Internal port:

```text
8000
```

---

## 4. Manager API Design

### 4.1 Recommended PoC Design

The Manager API runs as a small host-side service outside Docker.

The Launcher calls it through a controlled URL.

Example:

```text
http://host.docker.internal:9000
```

On Windows Docker Desktop, `host.docker.internal` is commonly available.

This host-side manager executes commands such as:

```text
docker compose start app1
docker compose stop app1
docker compose ps app1
```

This avoids mounting Docker socket into a container.

### 4.2 Alternative Design

The Manager API can run as a container only if it does not require Docker socket mount.

If Docker control is required, host-side Manager API is preferred.

### 4.3 Security Boundary

The Manager API must expose only limited operations.

Allowed operations:

```text
GET  /api/status
POST /api/start/app1
POST /api/start/app2
POST /api/start/app3
POST /api/start/app4
POST /api/stop/app1
POST /api/stop/app2
POST /api/stop/app3
POST /api/stop/app4
```

Disallowed operations:

- Arbitrary command execution
- Free text shell command execution
- Direct Docker socket exposure to Launcher
- Container creation from arbitrary image names
- File system access from web request

---

## 5. Network Architecture

Docker Compose creates one internal network.

Example network name:

```text
multiapp_net
```

All Docker services join this network:

```text
nginx
launcher
app1
app2
app3
app4
```

Nginx uses service names to forward requests.

Do not use fixed container IP addresses.

---

## 6. Routing Architecture

Nginx path routing:

```text
location /launcher/ {
    proxy_pass http://launcher:8000/;
}

location /app1/ {
    proxy_pass http://app1:8000/;
}

location /app2/ {
    proxy_pass http://app2:8000/;
}

location /app3/ {
    proxy_pass http://app3:8000/;
}

location /app4/ {
  proxy_pass http://app4:8000/;
}
```

Important note:

Because apps are served under subpaths, the application should generate relative URLs or be aware of its base path.

For the first PoC, use relative paths as much as possible.

---

## 7. Application Internal Architecture

Each app uses the same simple pattern.

```text
Browser page
  ↓ button click
Backend API
  ↓
JSON response
  ↓
Message displayed on page
```

Each app provides:

```text
GET /
GET /health
GET /api/test
```

Example `/api/test` response:

```json
{
  "status": "success",
  "message": "App1 backend responded successfully."
}
```

---

## 8. Launcher Internal Architecture

Launcher provides:

```text
GET /
GET /health
GET /api/apps
GET /api/status
POST /api/start/{app_name}
POST /api/stop/{app_name}
```

Launcher communicates with Manager API.

Launcher should not directly run Docker commands.

Launcher should not import Docker SDK unless explicitly approved.

---

## 9. Manager API Internal Architecture

Manager API provides controlled endpoints.

Example:

```text
GET  /health
GET  /api/status
GET  /api/status/app1
POST /api/start/app1
POST /api/stop/app1
```

Internally, Manager API may call a controlled script or command.

Example:

```text
docker compose start app1
docker compose stop app1
docker compose ps app1
```

The Manager API must validate app names.

Allowed app names:

```text
app1
app2
app3
app4
```

Any other app name must be rejected.

---

## 10. Folder Architecture

Target folder structure:

```text
docker-nginx-multiapp-test/
├─ .github/
│  └─ copilot-instructions.md
├─ docker-compose.yml
├─ README.md
├─ docs/
│  ├─ spec.md
│  ├─ architecture.md
│  └─ task.md
├─ nginx/
│  └─ nginx.conf
├─ manager-api/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ src/
│     └─ main.py
├─ launcher/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ src/
│     └─ main.py
├─ apps/
│  ├─ app1/
│  │  ├─ Dockerfile
│  │  ├─ requirements.txt
│  │  └─ src/
│  │     └─ main.py
│  ├─ app2/
│  │  ├─ Dockerfile
│  │  ├─ requirements.txt
│  │  └─ src/
│  │     └─ main.py
│  └─ app3/
│     ├─ Dockerfile
│     ├─ requirements.txt
│     └─ src/
│        └─ main.py
└─ scripts/
   ├─ start.bat
   ├─ stop.bat
   ├─ status.bat
   ├─ manager_start.bat
   └─ manager_stop.bat
```

---

## 11. Docker Compose Architecture

Expected services:

```text
nginx
launcher
app1
app2
app3
```

In the safer Method B design, `manager-api` may be launched outside Docker by a script.

Therefore, initial Docker Compose may include:

```text
nginx
launcher
app1
app2
app3
```

And the host-side manager is started separately:

```text
scripts/manager_start.bat
```

This separation makes Docker control safer and clearer for beginners.

---

## 12. Start and Stop Flow

### 12.1 Start Flow

```text
User
  ↓
Launcher Start Button
  ↓
Launcher API
  ↓
Manager API
  ↓
Controlled docker compose start app1
  ↓
Status returned to Launcher
```

### 12.2 Stop Flow

```text
User
  ↓
Launcher Stop Button
  ↓
Launcher API
  ↓
Manager API
  ↓
Controlled docker compose stop app1
  ↓
Status returned to Launcher
```

### 12.3 Open App Flow

```text
User
  ↓
Launcher Open Button
  ↓
Browser opens /app1/
  ↓
Nginx
  ↓
app1 container
```

---

## 13. Design Limitations

This architecture is safer than Docker socket mount, but it is still a PoC.

Before production use, consider:

- Authentication for Manager API
- IP restriction for Manager API
- HTTPS
- Logging
- Command timeout
- Strict command validation
- Running manager only on localhost
- Firewall rules

---

## 14. Future Extension

To add app4:

1. Create `apps/app4`
2. Add `app4` service to Docker Compose
3. Add Nginx location `/app4/`
4. Add app4 item to Launcher registration
5. Add app4 to Manager API allowed app list

---

## 15. Script Operation Layer

For reproducible local execution, operation scripts are organized under `scripts/` with a run-number convention.

Main entry scripts:

```text
run20_manager_start
run21_manager_stop
run35_docker_status
run40_nginx_check
run41_app_health_check
run42_manager_check
run50_start_all
run51_stop_all
```

Compatibility wrappers (`start`, `stop`, `status`, `manager_start`, `manager_stop`) delegate to these run scripts.

## 16. Dynamic registration architecture

The host-side Manager API owns `config/apps.json` and atomically persists
validated registrations. It generates `generated/docker-compose.apps.yml` and
`generated/nginx.conf`. Docker commands always use an argument array and the
generated Compose override; arbitrary shell input is not accepted.

Nginx mounts the generated configuration read-only. The Launcher only calls
Manager API and presents the registration and lifecycle operations; it never
accesses Docker or host files directly.
