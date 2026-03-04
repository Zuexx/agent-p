FROM ghcr.io/astral-sh/uv:python3.12-bookworm

# GIS 依賴
RUN apt-get update && apt-get install -y \
    git \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    proj-bin \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 下載 maptoposter
RUN git clone https://github.com/originalankur/maptoposter.git

# 建立虛擬環境
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# 安裝依賴
RUN uv pip install fastapi uvicorn requests
RUN uv pip install -r /app/maptoposter/requirements.txt

# 建立輸出資料夾
RUN mkdir -p /data

COPY /services/maptoposter/app.py /app/app.py

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]