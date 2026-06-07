# Base image block: use a small official Python runtime image.
FROM python:3.12-slim                     # Python runtime used by the application.

# Working directory block: set default folder for all next commands.
WORKDIR /app                              # All COPY/RUN/CMD paths are relative to /app.

# Environment block: make container logs immediate and avoid .pyc files.
ENV PYTHONDONTWRITEBYTECODE=1 \          # Disable bytecode file generation.
    PYTHONUNBUFFERED=1                    # Disable output buffering for clear logs.

# Dependency block: copy lock-like input and install Python packages.
COPY app/requirements.txt /app/app/requirements.txt  # Copy dependency list first.
RUN pip install --no-cache-dir -r /app/app/requirements.txt  # Install dependencies.

# Application source block: copy FastAPI source code into image.
COPY app /app/app                         # Copy the application package directory.

# Network block: document the internal app port used by uvicorn.
EXPOSE 8000                               # Container listens on TCP 8000.

# Startup block: launch the FastAPI app server.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]  # Entrypoint.
