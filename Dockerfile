FROM python:3.11-slim

# PORT, WEB_CONCURRENCY and DATABASE_URL are all overridable at run time.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    WEB_CONCURRENCY=2 \
    DATABASE_URL=sqlite:////data/students.db

WORKDIR /app

# Dependencies are installed before the source is copied so that code changes
# do not invalidate the cached dependency layer.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# The app runs as an unprivileged user and only needs write access to /data.
RUN adduser --system --group --no-create-home appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /data /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health').read()"

# Gunicorn supervises the workers and restarts them; the Uvicorn worker class is
# what actually speaks ASGI to this app.
CMD ["sh", "-c", "exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${WEB_CONCURRENCY} \
    --bind 0.0.0.0:${PORT} \
    --access-logfile - \
    --error-logfile -"]
