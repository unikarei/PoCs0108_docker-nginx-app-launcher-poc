# Task List: Docker + Nginx Multiple Web App Test Project

## Task Checkbox Rule

Each task title must start with a checkbox.

Use:

```text
[ ] Not completed
[x] Completed
```

When a task is completed, change `[ ]` to `[x]`.

Do not delete completed tasks. Keep them as project history.

## Phase 0: Preparation

### [x] Task 0.1 Create project folder

Create the base folder:

```text
docker-nginx-multiapp-test
```

### [x] Task 0.2 Create SDD documents

Create:

```text
.github/copilot-instructions.md
docs/spec.md
docs/architecture.md
docs/task.md
```

Status:

```text
[x] Done in Step 1
```

---

## Phase 1: Minimum App Implementation

### [x] Task 1.1 Create app1

Create app1 with:

```text
apps/app1/
├─ Dockerfile
├─ requirements.txt
└─ src/
   └─ main.py
```

Requirements:

- FastAPI app
- `GET /`
- `GET /health`
- `GET /api/test`
- Simple HTML page with one button
- Button shows success message

Expected message:

```text
App1 backend responded successfully.
```

### [x] Task 1.2 Create app2

Create app2 using same structure as app1.

Expected message:

```text
App2 backend responded successfully.
```

### [x] Task 1.3 Create app3

Create app3 using same structure as app1.

Expected message:

```text
App3 backend responded successfully.
```

---

## Phase 2: Launcher Implementation

### [x] Task 2.1 Create Launcher folder

Create:

```text
launcher/
├─ Dockerfile
├─ requirements.txt
└─ src/
   └─ main.py
```

### [x] Task 2.2 Create Launcher page

Launcher page must show:

- app1
- app2
- app3

Each app row must have:

- Status display
- Open button
- Start button
- Stop button

### [x] Task 2.3 Create Launcher API

Create Launcher endpoints:

```text
GET  /
GET  /health
GET  /api/apps
GET  /api/status
POST /api/start/{app_name}
POST /api/stop/{app_name}
```

### [x] Task 2.4 Connect Launcher to Manager API

Launcher must call Manager API for:

- status
- start
- stop

Launcher must not call Docker directly.

---

## Phase 3: Manager API Implementation

### [x] Task 3.1 Create Manager API folder

Create:

```text
manager-api/
├─ requirements.txt
└─ src/
   └─ main.py
```

Note:

In Method B, Manager API is preferably run on the host side, not inside Docker.

A Dockerfile for Manager API is optional in the first PoC.

### [x] Task 3.2 Create Manager API endpoints

Create:

```text
GET  /health
GET  /api/status
GET  /api/status/{app_name}
POST /api/start/{app_name}
POST /api/stop/{app_name}
```

### [x] Task 3.3 Validate app names

Allowed app names:

```text
app1
app2
app3
```

Reject all other names.

### [x] Task 3.4 Execute controlled Docker Compose commands

Manager API may execute:

```text
docker compose ps
docker compose start app1
docker compose stop app1
docker compose start app2
docker compose stop app2
docker compose start app3
docker compose stop app3
```

Do not allow arbitrary command strings from user input.

### [x] Task 3.5 Add command timeout and error handling

Add:

- timeout
- clear error message
- return code check
- stdout and stderr capture

---

## Phase 4: Docker Compose

### [x] Task 4.1 Create docker-compose.yml

Define services:

```text
nginx
launcher
app1
app2
app3
```

Do not expose host ports for:

```text
launcher
app1
app2
app3
```

Only expose:

```text
nginx:
  ports:
    - "8080:80"
```

### [x] Task 4.2 Create Docker internal network

Create:

```text
multiapp_net
```

Attach all services to it.

### [x] Task 4.3 Add health checks if simple

Add simple health checks if they do not make the configuration too complex.

---

## Phase 5: Nginx

### [x] Task 5.1 Create nginx folder

Create:

```text
nginx/
└─ nginx.conf
```

### [x] Task 5.2 Add reverse proxy settings

Add route rules:

```text
/launcher/ -> launcher:8000
/app1/     -> app1:8000
/app2/     -> app2:8000
/app3/     -> app3:8000
```

### [x] Task 5.3 Add proxy headers

Add standard proxy headers:

```text
Host
X-Real-IP
X-Forwarded-For
X-Forwarded-Proto
```

---

## Phase 6: Scripts

### [x] Task 6.1 Create start script

Create:

```text
scripts/run50_start_all.bat
scripts/run50_start_all.sh
scripts/start.bat
scripts/start.sh
```

Purpose:

```text
Start Manager API and Docker services in sequence.
```

### [x] Task 6.2 Create stop script

Create:

```text
scripts/run51_stop_all.bat
scripts/run51_stop_all.sh
scripts/stop.bat
scripts/stop.sh
```

Purpose:

```text
Stop Docker services and Manager API in sequence.
```

### [x] Task 6.3 Create status script

Create:

```text
scripts/run35_docker_status.bat
scripts/run35_docker_status.sh
scripts/status.bat
scripts/status.sh
```

Purpose:

```text
docker compose ps
```

### [x] Task 6.4 Create Manager API start script

Create:

```text
scripts/run20_manager_start.bat
scripts/run20_manager_start.sh
scripts/manager_start.bat
scripts/manager_start.sh
```

Purpose:

Start host-side Manager API.

Example behavior:

```text
cd manager-api
python -m uvicorn src.main:app --host 127.0.0.1 --port 9000
```

### [x] Task 6.5 Create Manager API stop script

Create:

```text
scripts/run21_manager_stop.bat
scripts/run21_manager_stop.sh
scripts/manager_stop.bat
scripts/manager_stop.sh
```

Purpose:

Stop host-side Manager API.

For first PoC, it may only show instructions.

---

## Phase 7: Verification

### [x] Task 7.1 Start Manager API

Run:

```text
scripts/run20_manager_start.bat
or scripts/manager_start.bat
```

Confirm:

```text
http://127.0.0.1:9000/health
```

### [x] Task 7.2 Start Docker services

Run:

```text
scripts/run32_docker_start_detached.bat
or scripts/start.bat
```

### [x] Task 7.3 Confirm Docker status

Run:

```text
scripts/run35_docker_status.bat
or scripts/status.bat
```

### [x] Task 7.4 Open Launcher

Open:

```text
http://localhost:8080/launcher/
```

### [x] Task 7.5 Open each app

Open:

```text
http://localhost:8080/app1/
http://localhost:8080/app2/
http://localhost:8080/app3/
http://localhost:8080/app4/
```

### [x] Task 7.6 Test buttons

Click the test button in each app.

Expected:

```text
App1 backend responded successfully.
App2 backend responded successfully.
App3 backend responded successfully.
App4 backend responded successfully.
```

### [x] Task 7.7 Test Launcher status

Click status button or reload Launcher.

Expected:

```text
running
stopped
unknown
```

### [x] Task 7.8 Test Launcher start and stop

Use Launcher buttons to:

- stop app1
- start app1
- stop app2
- start app2
- stop app3
- start app3
- stop app4
- start app4

Confirm status changes.

---

## Phase 8: README

### [x] Task 8.1 Create README

README must include:

- Project purpose
- Architecture summary
- Folder structure
- How to start Manager API
- How to start Docker services
- How to access Launcher
- How to access each app
- How to stop services
- Security note about Manager API
- Future extension method

---

## Phase 9: Future Improvements

These tasks are not required in the first PoC.

### [x] Task 9.1 Add Basic authentication to Launcher

### [x] Task 9.2 Add HTTPS

### [x] Task 9.3 Add app4

### [x] Task 9.4 Add logs

### [x] Task 9.5 Add production Nginx configuration

### [x] Task 9.6 Add Linux shell scripts

### [x] Task 9.7 Add GitHub Actions

