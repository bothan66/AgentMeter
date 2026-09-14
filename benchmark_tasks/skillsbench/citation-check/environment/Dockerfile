FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN echo 'registry=https://registry.npmmirror.com' > /root/.npmrc
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' /etc/apt/sources.list.d/ubuntu.sources \
    && sed -i 's|http://security.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' /etc/apt/sources.list.d/ubuntu.sources

# Install Python and essential tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    curl \
    ca-certificates \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @qwen-code/qwen-code@latest

# Pre-install uv to avoid GitHub download in test.sh
RUN pip3 install --break-system-packages uv==0.9.7 && \
    mkdir -p /root/.local/bin && \
    cp $(which uv) /root/.local/bin/uv && \
    cp $(which uvx) /root/.local/bin/uvx && \
    printf '#!/bin/sh\nexport PATH="/root/.local/bin:$PATH"\n' > /root/.local/bin/env && \
    chmod +x /root/.local/bin/env

# Install Python dependencies for citation verification
RUN pip3 install --break-system-packages \
    requests==2.32.3 \
    bibtexparser==1.4.2

# Create working directory
WORKDIR /root

# Copy the test.bib file to /root
COPY test.bib /root/test.bib

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
