# GitHub Copilot Instructions

## 1. Project Overview

This project is a Proof of Concept for managing multiple web applications using Docker internal networking and Nginx reverse proxy.

The goal is to verify the following architecture:

- Multiple web applications run as Docker services.
- Only Nginx exposes a host-side port.
- Each application is accessed through Nginx path-based routing.
- Applications communicate through Docker internal network service names.
- A Launcher application provides a GUI to open, check, start, and stop each app.
- Start and stop operations are handled through a safer host-side management API, not by mounting Docker socket into the Launcher container.

This project follows SDD, Spec-Driven Development.

Copilot must follow these documents:

```text
docs/spec.md
docs/architecture.md
docs/task.md
```

Do not implement features that are not described in these documents unless explicitly requested.

---

## 2. Development Rule

Always proceed in the following order:

1. Read `docs/spec.md`
2. Read `docs/architecture.md`
3. Read `docs/task.md`
4. Implement only the current task
5. Keep the implementation simple and readable
6. Do not add unnecessary frameworks or complex mechanisms

This is a test application, not a production application.

---

## 3. Important Architecture Rules

The most important rule is:

```text
Only Nginx exposes ports to the host.
```

The following services must not expose host-side ports directly:

- launcher
- app1
- app2
- app3

They should only expose internal container ports.

Nginx routes requests to each service using Docker Compose service names.

Example:

```text
http://launcher:8000
http://app1:8000
http://app2:8000
http://app3:8000
```

Do not use container IP addresses.

---

## 4. Security Rule for Start and Stop Operations

Do not mount Docker socket into the Launcher container.

The following is prohibited:

```yaml
- /var/run/docker.sock:/var/run/docker.sock
```

Instead, use the safer architecture described in `docs/architecture.md`.

The Launcher sends requests to a host-side management API.

The host-side management API executes controlled start, stop, and status commands.

This is called Method B in the specification.

---

## 5. Target Services

The system consists of the following services:

```text
nginx
launcher
app1
app2
app3
manager-api
```

The `manager-api` is responsible for start, stop, and status operations.

---

## 6. URL Routing Rule

Use the following routing design:

```text
/launcher/  -> launcher
/app1/      -> app1
/app2/      -> app2
/app3/      -> app3
```

The Launcher should provide buttons or links to open each app through these URLs.

---

## 7. Application Rule

Each test app should be very simple.

Each of `app1`, `app2`, and `app3` must have:

- A simple GUI page
- One test button
- One backend endpoint
- A success message when the button is clicked

Example messages:

```text
App1 backend responded successfully.
App2 backend responded successfully.
App3 backend responded successfully.
```

---

## 8. Folder Structure Rule

Use this structure as the base:

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

## 9. Implementation Preference

Use simple Python FastAPI applications unless otherwise instructed.

Preferred stack:

- Python
- FastAPI
- Uvicorn
- Docker
- Docker Compose
- Nginx

Use plain HTML inside FastAPI responses for the first implementation.

Do not use React, Vue, Next.js, or other frontend frameworks in the initial PoC.

---

## 10. Coding Style

Write code that is easy for beginners to understand.

Use:

- Clear function names
- Simple comments
- Small files
- Explicit error messages
- Minimal dependencies

Avoid:

- Hidden magic
- Over-engineering
- Complex class structures
- Unnecessary async complexity
- Large frontend frameworks

---

## 11. Completion Criteria

The implementation is complete when the following URLs work through Nginx:

```text
http://localhost:8080/launcher/
http://localhost:8080/app1/
http://localhost:8080/app2/
http://localhost:8080/app3/
```

And each app button returns a success message.

The Launcher must also be able to:

- show app status
- request app start
- request app stop
- open each app

Start and stop requests must go through `manager-api`.

---

## 12. Do Not Change Without Permission

Do not change the architecture from Method B to Docker socket mount.

Do not expose app1, app2, app3, launcher directly to host ports.

Do not add database or authentication in the first PoC.

Do not add SSL in the first PoC unless explicitly requested.

Do not create Kubernetes configuration.

