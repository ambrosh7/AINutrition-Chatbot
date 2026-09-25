FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY data/ /app/data/

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:create_app --factory --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}"]
