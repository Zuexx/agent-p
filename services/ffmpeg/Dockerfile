FROM ghcr.io/astral-sh/uv:python3.12-bookworm

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

RUN uv pip install fastapi uvicorn requests

RUN mkdir -p /data

COPY /service/ffmpeg/app.py /app/app.py

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]