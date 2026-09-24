# Purpose: package the API, frontend and worker for a single-origin Linux deployment.
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY backend backend
COPY database database
COPY orchestrator orchestrator
COPY sub_agents sub_agents
COPY integrations integrations
COPY prompts prompts
COPY frontend frontend
COPY scripts scripts
COPY alembic.ini .
RUN useradd --create-home appuser && mkdir -p /app/data/documents && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
