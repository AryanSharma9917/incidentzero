FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app /app/backend/app
COPY sandbox/base /app/sandbox/base
COPY sandbox/incidents /app/sandbox/incidents
RUN useradd --create-home --uid 10001 incidentzero && mkdir /data && chown incidentzero:incidentzero /data
USER incidentzero
ENV DATABASE_PATH=/data/incidentzero.sqlite3 EXECUTION_MODE=simulation RUNS_ENABLED=false
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
