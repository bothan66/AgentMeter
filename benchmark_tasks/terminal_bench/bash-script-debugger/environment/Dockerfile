FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN if [ -f /etc/apt/sources.list ]; then \
      sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list; \
      sed -i 's|http://security.debian.org|http://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list; \
    else \
      find /etc/apt/sources.list.d/ -name "*.sources" -exec sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' {} \; ; \
    fi

RUN pip install --no-cache-dir uv==0.6.14 && \
    mkdir -p /root/.local/bin && \
    cp $(which uv) /root/.local/bin/uv && \
    cp $(which uvx) /root/.local/bin/uvx

WORKDIR /app
RUN mkdir -p /app/scripts

# Write the buggy deploy.sh with exactly 5 deliberate bugs.
# Bug categories (matching hint in instruction.md):
#   Bug1 - wrong file-test operator: [ -d ... ] instead of [ ! -f ... ]
#   Bug2 - mkdir without -p flag
#   Bug3 - unquoted variable ($DEPLOY_PATH) causing word-splitting risk
#   Bug4 - > overwrites log instead of >> appending
#   Bug5 - missing export: APP_ENV not visible to child processes
COPY generate_data.py /tmp/generate_data.py
RUN python3 /tmp/generate_data.py

RUN chmod +x /app/scripts/deploy.sh
