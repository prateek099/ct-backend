# ── Base ──────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base
WORKDIR /app

RUN pip install poetry==1.8.2
ENV POETRY_VENV_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1

COPY pyproject.toml poetry.lock* ./

# ── Development ───────────────────────────────────────────────────────────────
FROM base AS development
RUN poetry install --with dev
COPY . .
CMD ["poetry", "run", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Builder (prod deps only) ──────────────────────────────────────────────────
FROM base AS builder
RUN poetry install --only main --no-root
RUN poetry export --without-hashes -f requirements.txt -o requirements.txt

# ── Production ────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS production
WORKDIR /app

RUN useradd -m appuser

COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
