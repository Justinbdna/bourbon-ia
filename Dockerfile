# ══════════════════════════════════════════════════════════════════════════
# Bourbon.IA — Dockerfile Multi-Stage 100 % Souverain & Air-Gapped
# ══════════════════════════════════════════════════════════════════════════
# Étape 1 : Build de l'interface React / Vite
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.js tailwind.config.js postcss.config.js ./
COPY public ./public
COPY src ./src

ENV VITE_AI_PROVIDER_DEFAUT=local
RUN npm run build

# Étape 2 : Runtime Backend FastAPI / Uvicorn & Serveur MCP
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BOURBON_TEXTES_DISTANTS=0 \
    BOURBON_MAX_AMENDEMENTS=25000 \
    BOURBON_RAG_DB_PATH=/app/data/bourbon_rag.db

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY mcp_server.py ./mcp_server.py
COPY --from=frontend-builder /app/frontend/dist ./dist

RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8000

CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000"]
