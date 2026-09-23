FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-rus && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY .claude/skills/sro-odo /app/.claude/skills/sro-odo
COPY odo-app /app/odo-app
RUN pip install --no-cache-dir -r /app/odo-app/requirements.txt
WORKDIR /app/odo-app
ENV ODO_HOST=0.0.0.0 ODO_PORT=8765 ODO_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8765
CMD ["python", "-m", "server"]
