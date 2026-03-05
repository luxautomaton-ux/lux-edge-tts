FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir git+https://github.com/rany2/edge-tts.git -r requirements.txt

COPY app.py .

ENV PORT=3000
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-3000}
