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

RUN mkdir -p /app/data /app/output

# Generate employees.csv with ~50 rows and exactly 8 deliberate errors:
#   Error 1  (row 5):  invalid email (no @)
#   Error 2  (row 9):  duplicate employee_id (same as row 2)
#   Error 3  (row 14): salary too low (500, below minimum 1000)
#   Error 4  (row 18): salary too high (600000, above maximum 500000)
#   Error 5  (row 23): hire_date in the future (2025-06-01, after 2024-01-01)
#   Error 6  (row 31): hire_date invalid format (not YYYY-MM-DD)
#   Error 7  (row 37): invalid email (no dot after @)
#   Error 8  (row 44): manager_id references non-existent employee_id (9999)
COPY generate_data.py /tmp/generate_data.py
RUN python3 /tmp/generate_data.py
