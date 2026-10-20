# 1) Build the Vue frontend
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2) Python backend that also serves the built frontend
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv
WORKDIR /app/backend
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/src ./src
RUN uv sync --frozen --no-dev
COPY --from=web /web/dist /app/frontend/dist
ENV FRONTEND_DIST=/app/frontend/dist PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uv run --no-dev uvicorn matchvoice.main:app --host 0.0.0.0 --port ${PORT}"]
