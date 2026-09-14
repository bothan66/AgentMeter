FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' /etc/apt/sources.list.d/ubuntu.sources \
    && sed -i 's|http://security.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' /etc/apt/sources.list.d/ubuntu.sources

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @openai/codex@latest @qwen-code/qwen-code@latest

RUN pip3 install --break-system-packages uv==0.9.7 && \
    mkdir -p /root/.local/bin && \
    cp $(which uv) /root/.local/bin/uv && \
    cp $(which uvx) /root/.local/bin/uvx && \
    printf '#!/bin/sh\nexport PATH="/root/.local/bin:$PATH"\n' > /root/.local/bin/env && \
    chmod +x /root/.local/bin/env

WORKDIR /app
