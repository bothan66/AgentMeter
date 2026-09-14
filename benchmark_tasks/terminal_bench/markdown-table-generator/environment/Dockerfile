FROM python:3.11-slim

ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN pip install uv==0.9.7 && \
    mkdir -p /root/.local/bin && \
    cp $(which uv) /root/.local/bin/uv && \
    cp $(which uvx) /root/.local/bin/uvx && \
    printf '#!/bin/sh\nexport PATH="/root/.local/bin:$PATH"\n' > /root/.local/bin/env && \
    chmod +x /root/.local/bin/env

WORKDIR /app

RUN mkdir -p /app/data /app/output

COPY generate_data.py /tmp/generate_data.py
RUN python3 /tmp/generate_data.py
