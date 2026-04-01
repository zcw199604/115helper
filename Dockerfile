# syntax=docker/dockerfile:1.7

FROM node:24-alpine AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/app/data \
    DB_DIR=/app/db \
    SQLITE_PATH=/app/db/app.db
WORKDIR /app

COPY backend/ ./backend/
RUN pip install --upgrade pip && pip install ./backend

COPY --from=frontend-builder /build/frontend/dist ./frontend/dist
COPY .env.example ./
RUN mkdir -p /app/data /app/db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
