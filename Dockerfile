# Multi-stage build for ECS Express Mode, which deploys from a pre-built
# image in ECR (no build-from-source-from-git option, unlike the old App
# Runner plan) — see README.md's Decisions log, 2026-08-15.
#
# Stage 1 builds the frontend; stage 2 serves it as static assets from the
# same FastAPI container the backend runs in, preserving the "one deployable"
# architecture (README.md Tech stack, CLAUDE.md Deployment shape).

FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Not secrets (this Cognito app client has no client secret) — defaults match
# the real pool, so a plain `docker build` works unchanged; override via
# --build-arg for a different environment/pool. Vite inlines VITE_-prefixed
# vars from process.env at `npm run build` time, so these must be ENV, not
# just ARG, before the build step runs.
ARG VITE_COGNITO_REGION=us-east-2
ARG VITE_COGNITO_APP_CLIENT_ID=4tpkjhn2v74cjr9rbmca3kjih8
ENV VITE_COGNITO_REGION=${VITE_COGNITO_REGION}
ENV VITE_COGNITO_APP_CLIENT_ID=${VITE_COGNITO_APP_CLIENT_ID}
RUN npm run build

FROM python:3.13-slim AS backend
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ ./
RUN uv sync --frozen --no-dev

COPY --from=frontend-build /frontend/dist ./src/aplit_grader/static

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["uvicorn", "aplit_grader.main:app", "--host", "0.0.0.0", "--port", "8000"]
