# Codex Agent Instructions

## Project and source of truth

This repository is a beginner-friendly, Spec-Driven Development (SDD) proof of
concept for running multiple web applications behind an Nginx reverse proxy.

Before changing implementation, read these documents in order:

1. `docs/spec.md`
2. `docs/architecture.md`
3. `docs/task.md`

Treat them as the source of truth. Implement only behavior described there or
explicitly requested by the user. If a requested change affects requirements,
architecture, routes, services, or operations, update the relevant SDD document
first, then implement the matching task.

## SDD workflow

1. Identify the relevant unchecked task in `docs/task.md`.
2. Make the smallest clear implementation needed for that task.
3. Verify the change with focused checks appropriate to the files changed.
4. Mark that task `[x]` only after verification succeeds. Keep completed tasks
   in the document as project history.
5. Report changed files, verification performed, and any remaining limitation.

Do not add unrelated features, frameworks, or production infrastructure.

## Architecture invariants

- Nginx is the only Docker service allowed to publish a host-side port
  (`8080:80` for development).
- `launcher` and every `app*` service communicate only through Docker internal
  networking. Do not publish their ports or use container IP addresses; use
  Compose service names.
- Use Nginx path routing such as `/launcher/`, `/app1/`, `/app2/`, `/app3/`,
  and `/app4/`. Applications should use relative URLs so they work below their
  routed base path.
- The Launcher never executes Docker commands and must not use the Docker SDK.
- Never mount `/var/run/docker.sock` into the Launcher (or expose Docker Engine
  access through it).
- Management actions go through the host-side `manager-api` (Method B). It must
  accept only the documented app names and controlled status/start/stop
  operations—never arbitrary shell commands or request-provided command text.
- Keep Manager API bound and accessed as documented; do not expose it through
  Nginx unless the SDD documents are deliberately revised.

## Implementation conventions

- Prefer Python, FastAPI, Uvicorn, Docker Compose, Nginx, and plain HTML.
- Keep code small, explicit, and readable for beginners. Use clear names,
  simple functions, minimal dependencies, and useful error messages.
- Avoid React, Vue, Next.js, databases, authentication, HTTPS, Kubernetes,
  and unnecessary async or abstraction unless explicitly requested and added to
  the SDD documents.
- Preserve the established app contract: `GET /`, `GET /health`, and
  `GET /api/test` for each test app; app-specific success messages should remain
  explicit.
- Preserve the scripts under `scripts/` and their run-number convention for
  reproducible startup, shutdown, status, and health checks.

## Verification

For Docker, Nginx, routing, or service changes, use the repository scripts
where applicable (notably `run35_docker_status`, `run40_nginx_check`,
`run41_app_health_check`, and `run42_manager_check`) and verify the affected
route or endpoint. Do not claim Docker verification if Docker Desktop or the
host-side Manager API is not running; state the limitation instead.

Keep the repository's current worktree changes intact. Do not overwrite or
revert unrelated user changes.
