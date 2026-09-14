FROM python:3.11-slim

ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN pip install uv==0.9.7 && \
    mkdir -p /root/.local/bin && \
    cp $(which uv) /root/.local/bin/uv && \
    cp $(which uvx) /root/.local/bin/uvx

WORKDIR /app
