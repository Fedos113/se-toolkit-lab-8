# Multi-stage build for nanobot, following the pattern of backend/Dockerfile.

# ---
# Stage 1: build the application in the `/app` directory.
# ---

ARG REGISTRY_PREFIX_DOCKER_HUB
FROM ${REGISTRY_PREFIX_DOCKER_HUB}astral/uv:python3.14-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

# Disable Python downloads - use the system interpreter across both images.
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy workspace root files
COPY --from=workspace pyproject.toml uv.lock /app/

# Copy nanobot project files
COPY --from=workspace nanobot/ ./nanobot/

# Copy MCP servers that nanobot depends on
COPY --from=workspace mcp/ ./mcp/

# Copy nanobot-websocket-channel packages
COPY --from=workspace nanobot-websocket-channel/ ./nanobot-websocket-channel/

# Install nanobot dependencies from the workspace root
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package nanobot

# ---
# Stage 2: use a final image without uv
# ---

ARG REGISTRY_PREFIX_DOCKER_HUB
FROM ${REGISTRY_PREFIX_DOCKER_HUB}python:3.14.2-slim-bookworm

# Set environment variables for Python and application
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Make sure we use UTF-8 encoding
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends gosu && rm -rf /var/lib/apt/lists/*

# Create non-root user; accept APP_UID/APP_GID for host-user bind-mount compatibility
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd --system --gid "${APP_GID}" appuser \
    && useradd --system --gid "${APP_GID}" --uid "${APP_UID}" --create-home appuser

# Copy the application from the builder
COPY --from=builder --chown=appuser:appuser /app /app

# Create writable directory for nanobot workspace
RUN chown -R appuser:appuser /app/nanobot

# Use the app user to run the application
USER appuser

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

CMD ["python", "/app/nanobot/entrypoint.py"]
