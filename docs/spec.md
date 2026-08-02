# Specification: Docker + Nginx Multiple Web App Test Project

## 1. Purpose

This project is a Proof of Concept for verifying a clean multi-web-application operation model using Docker and Nginx.

The purpose is not to create a production-grade service.

The purpose is to confirm that:

- Multiple web applications can run as separate Docker services.
- Nginx can act as the single entrance point.
- Docker internal network can connect Nginx and applications.
- Host-side port pollution can be avoided.
- Applications can be accessed by URL path instead of remembering port numbers.
- A Launcher GUI can manage app access, status, start, and stop.

---

## 2. Main Concept

The system uses this concept:

```text
Browser
  ↓
Nginx
  ↓
Docker internal network
  ↓
launcher / app1 / app2 / app3 / app4
```

Only Nginx is exposed to the host.

Each app runs inside Docker and is reached by Nginx through service names.

---

## 3. Applications

The project contains five user-facing applications.

### 3.1 Launcher

The Launcher is the main control screen.

It provides:

- List of app1, app2, app3, app4
- App status display
- Start button
- Stop button
- Open button

The Launcher does not execute Docker commands directly.

The Launcher sends start, stop, and status requests to the management API.

### 3.2 App1

App1 is a simple test web application.

Required functions:

- Show title: `App1`
- Show one button
- Send request to backend API when the button is clicked
- Show success message from backend

Expected success message:

```text
App1 backend responded successfully.
```

### 3.3 App2

App2 is a simple test web application.

Expected success message:

```text
App2 backend responded successfully.
```

### 3.4 App3

App3 is a simple test web application.

Expected success message:

```text
App3 backend responded successfully.
```

### 3.5 App4

App4 is a simple test web application.

Expected success message:

```text
App4 backend responded successfully.
```

---

## 4. Manager API

The Manager API is a local management service.

It handles controlled operations for Docker Compose services.

Required functions:

- Get status of app1, app2, app3, app4
- Start app1, app2, app3, app4
- Stop app1, app2, app3, app4

The Manager API is introduced to avoid mounting Docker socket into the Launcher container.

This is safer than giving the Launcher direct Docker Engine access.

---

## 5. User Operations

### 5.1 Open Launcher

User opens:

```text
http://localhost:8080/launcher/
```

The Launcher screen appears.

### 5.2 Open Each App

From Launcher, user can open:

```text
http://localhost:8080/app1/
http://localhost:8080/app2/
http://localhost:8080/app3/
http://localhost:8080/app4/
```

### 5.3 Test Each App

In app1, app2, app3, and app4:

1. User opens app page.
2. User clicks test button.
3. App calls its own backend endpoint.
4. Success message is shown.

### 5.4 Start App

In Launcher:

1. User clicks start button.
2. Launcher sends request to Manager API.
3. Manager API executes controlled start operation.
4. Launcher refreshes status.

### 5.5 Stop App

In Launcher:

1. User clicks stop button.
2. Launcher sends request to Manager API.
3. Manager API executes controlled stop operation.
4. Launcher refreshes status.

---

## 6. URL Specification

Nginx routes URLs as follows:

```text
/launcher/  -> launcher
/app1/      -> app1
/app2/      -> app2
/app3/      -> app3
/app4/      -> app4
```

Health check URLs:

```text
/launcher/health
/app1/health
/app2/health
/app3/health
/app4/health
```

Test API URLs:

```text
/app1/api/test
/app2/api/test
/app3/api/test
/app4/api/test
```

Manager API should not be publicly exposed through Nginx in the first design.

The Launcher may communicate with Manager API through the internal Docker network or a controlled host-side address depending on implementation.

---

## 7. Docker Requirement

Docker Compose must define these services:

```text
nginx
launcher
app1
app2
app3
app4
manager-api
```

In Method B operation, manager-api may run on host side.

Only `nginx` exposes a host port.

Development port:

```text
8080:80
```

The other services use internal Docker networking only.

---

## 8. Functional Requirements

### FR-001: Nginx Single Entry

The user can access all applications through Nginx.

### FR-002: App1 Test Button

App1 has a button and returns a success message.

### FR-003: App2 Test Button

App2 has a button and returns a success message.

### FR-004: App3 Test Button

App3 has a button and returns a success message.

### FR-005: Launcher App List

Launcher shows app1, app2, and app3.

### FR-006: Launcher Open Button

Launcher can open each app through Nginx path URLs.

### FR-007: Launcher Status Button

Launcher can show each app status.

### FR-008: Launcher Start Button

Launcher can request Manager API to start each app.

### FR-009: Launcher Stop Button

Launcher can request Manager API to stop each app.

### FR-010: No Direct App Host Port

app1, app2, app3, app4, and launcher must not publish host-side ports.

### FR-011: Scripted Operation Flow

The project provides run scripts under `scripts/` for startup, shutdown, status, and checks.

Primary scripts:

- `run50_start_all` for start sequence
- `run51_stop_all` for stop sequence
- `run35_docker_status` for compose status
- `run40_nginx_check` for route checks
- `run41_app_health_check` for health checks
- `run42_manager_check` for Manager API checks

---

## 9. Non-Functional Requirements

### NFR-001: Simplicity

Implementation must be simple and easy to understand.

### NFR-002: Beginner Friendly

Code and configuration should be readable for a beginner.

### NFR-003: Expandability

Adding app4 in the future should require only:

- app4 folder
- one Docker Compose service
- one Nginx location rule
- one Launcher registration item

### NFR-004: Security Direction

The system must not mount Docker socket into Launcher.

Start and stop operations must be isolated through Manager API.

### NFR-005: Port Cleanliness

The host machine should not be polluted by many public ports.

---

## 10. Out of Scope

The following are not included in the first PoC:

- User login
- Database
- HTTPS
- SSL certificate
- Production deployment
- Kubernetes
- CI/CD
- Cloud deployment
- Advanced frontend framework
- Complex permission control

---

## 11. Success Criteria

The project is successful when:

1. `docker compose up -d` starts Nginx, Launcher, and test apps.
2. User can open `http://localhost:8080/launcher/`.
3. User can open app1, app2, and app3 through Nginx paths.
4. Each app button returns a success message.
5. `docker compose ps` shows the expected services.
6. App services are not directly exposed to host ports.
7. Launcher can request status, start, and stop through Manager API.
8. The architecture does not use Docker socket mount in Launcher.

## 12. Dynamic Application Management Extension

Launcher and Manager API also manage persisted application registrations in
`config/apps.json`. Each registration separates `display_name`, `app_id`, and
`source_directory`, and includes route, port, health path, Dockerfile,
description, enabled flag, and timestamps.

Manager API exposes validated CRUD and lifecycle operations (`list`, `inspect`,
`add`, `update`, `remove`, `start`, `stop`, `restart`, `rebuild`, `logs`).
Generated Compose and Nginx files are written under `generated/`; they are
derived artifacts and must not be edited by hand. Existing app1-app4 entries
remain in the initial configuration.
