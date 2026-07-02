# --- Backend Dockerfile ---
# Design decision: single-stage build. A multi-stage build (builder + slim
# runtime) would shave ~50-80MB off the final image, but this project has no
# compiled dependencies requiring build tools that must be excluded from the
# final image, so the added Dockerfile complexity isn't worth it at this
# project's scale. Revisit if adding a dependency that needs gcc/build-essential.
FROM python:3.11-slim

WORKDIR /app

# Install system deps needed by some Python packages' wheels (bcrypt, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/media_storage

EXPOSE 8000

# --workers 1 by default: LangGraph's compiled graph and the OpenAI/Motor
# clients are all safe to share within a worker, but running >1 worker means
# >1 Motor connection pool and >1 OpenAI client — fine, but size WEB_CONCURRENCY
# to your Render plan's CPU count rather than guessing here. See README.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
