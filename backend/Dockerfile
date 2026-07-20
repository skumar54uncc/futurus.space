# Cloud Run / container deploys: build context must be backend/
FROM python:3.11-slim
WORKDIR /app

# WeasyPrint pulls pycairo — needs a compiler + *-dev headers at pip install time, not only runtime .so libs.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config \
    libcairo2-dev libpango1.0-dev libgdk-pixbuf-2.0-dev libffi-dev libglib2.0-dev \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi8 shared-mime-info fonts-dejavu-core \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional (disabled by default): install heavyweight TimesFM deps when full model mode is required.
# COPY requirements.timesfm.txt .
# RUN pip install --no-cache-dir -r requirements.timesfm.txt

COPY . .

# Cloud Run injects PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

# Inline sims only on Cloud Run (no Celery worker). Keep request timeout high on the service.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
