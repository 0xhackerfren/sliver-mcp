FROM python:3.12-slim

LABEL maintainer="SuzuLabs"
LABEL description="Sliver MCP Server - Production-grade agentic red team platform"

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

RUN python check.py

ENTRYPOINT ["sliver-mcp"]
