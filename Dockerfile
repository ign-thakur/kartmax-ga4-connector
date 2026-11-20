# KartmaX GA4 Connector — API + optional dashboard (controlled by ENABLE_DASHBOARD).
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
  PYTHONPATH=/app

WORKDIR /app

RUN groupadd --system --gid 1001 connector \
    && useradd --system --uid 1001 --gid connector connector

COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt -c constraints.txt

COPY src ./src

USER connector

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "src.dashboard.app:app", "--host", "0.0.0.0", "--port", "8080"]