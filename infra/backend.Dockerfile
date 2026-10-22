FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=UTC
WORKDIR /app
COPY backend/requirements.txt backend/constraints.txt /app/backend/
RUN pip install --no-cache-dir -c backend/constraints.txt -r backend/requirements.txt && useradd --uid 10001 --create-home metrologia
COPY backend /app/backend
COPY database /app/database
COPY alembic.ini /app/alembic.ini
USER 10001
