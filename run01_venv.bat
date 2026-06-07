This repository is Docker-first and does not require a local Python virtual environment for the standard workflow.

What this file is for:
- It exists as a compatibility note for older runbooks that referenced a local venv bootstrap step.
- The current supported workflow is to use Docker for application runtime and dependency management.
- If you are following the main setup path, prefer the Docker scripts instead of trying to build or activate a local .venv from here.

Current recommended entry points:
- run30_docker_init.bat
- run31_docker_start_dev.bat
- run32_docker_start_prd.bat
- run33_docker_stop.bat
- run34_docker_log.bat

If you intentionally want to keep a separate Python environment for experiments, use the uv-based scripts in the run10/run11 family, but that is outside the default project flow.
