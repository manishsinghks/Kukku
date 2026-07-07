# Kukku — containerized deployment.
# NOTE: inside Docker the assistant cannot open macOS apps or lock the screen,
# and it only sees the host directories you mount. Running natively via
# scripts/start.sh (or the launchd plist) is recommended on a Mac.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /jarvis
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY .env.example .

ENV DATA_DIR=/jarvis/data
VOLUME ["/jarvis/data"]
EXPOSE 8788

CMD ["python", "-m", "app.main"]
