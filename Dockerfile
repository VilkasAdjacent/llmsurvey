# Stage 1: build React frontend
FROM node:24-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python server
FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY llmsurvey/ ./llmsurvey/
COPY templates/ ./templates/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8000
CMD ["llmsurvey", "serve", "--host", "0.0.0.0", "--surveys-dir", "/data/surveys"]
