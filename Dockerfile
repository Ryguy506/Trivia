# Build the web app
FROM node:22-slim AS web
WORKDIR /web
COPY UI/web/package.json UI/web/package-lock.json ./
RUN npm ci
COPY UI/web/ ./
RUN npm run build

# Backend, serving the built web app from /app/static
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"
COPY trivia-backend/pyproject.toml trivia-backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
# Pre-fetch the Wikipedia MCP server so the first research round doesn't download it
RUN uvx --from wikipedia-mcp@2.0.1 python -c "import wikipedia_mcp"
COPY trivia-backend/ ./
COPY --from=web /web/dist ./static
EXPOSE 8000
# Hosts like Railway and Render set PORT; one worker, since rooms live in memory
CMD fastapi run app/main.py --port ${PORT:-8000}
