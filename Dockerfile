FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs containers as uid 1000.
RUN useradd -m -u 1000 user

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .
RUN chown -R user:user /app

USER user

ENV PYTHONPATH=/app/src \
    HOME=/home/user \
    PORT=7860

# Hugging Face Spaces expects the app on port 7860 (app_port in README).
EXPOSE 7860

CMD ["sh", "-c", "uvicorn usdent.api:app --host 0.0.0.0 --port ${PORT:-7860}"]
