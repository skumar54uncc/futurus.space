# DigitalOcean App Platform / container deploys: build context must be backend/
FROM python:3.11-slim
WORKDIR /app

# WeasyPrint + GDK-Pixbuf loaders (PDF export); xhtml2pdf works without these but both are in requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi8 shared-mime-info fonts-dejavu-core \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# App Platform and Railway inject PORT
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
