# china-law-mcp · 中国法律条文 MCP 服务器
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    CHINA_LAW_DB=/app/data/laws.db

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/laws.db ./data/laws.db

ENV PYTHONPATH=/app/src

# 预构建 BM25 索引（约 6s），让容器启动后调用工具无需等待
RUN python scripts/build_index.py

# MCP 走 stdio，必须前台运行
ENTRYPOINT ["python", "-m", "china_law_mcp"]
