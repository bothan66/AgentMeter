            FROM python:3.11.9-slim-bookworm

            ENV DEBIAN_FRONTEND=noninteractive
            ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

            RUN if [ -f /etc/apt/sources.list ]; then \
                  sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list; \
                  sed -i 's|http://security.debian.org|http://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list; \
                else \
                  find /etc/apt/sources.list.d/ -name "*.sources" -exec sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' {} \; ; \
                fi

            RUN pip install \
                pandas==2.2.2 \
                numpy==1.26.4 \
                scipy==1.13.0 \
                scikit-learn==1.5.0 \
                matplotlib==3.9.0 \
                statsmodels==0.14.2 \
                openpyxl==3.1.2 \
                pyarrow==16.0.0 \
                fuzzywuzzy==0.18.0 \
                python-Levenshtein==0.25.1 \
                json5==0.9.28 \
                joblib==1.4.2

            WORKDIR /app
            RUN mkdir -p /app/data /app/output

            COPY Books_df.csv /app/data/
COPY Genre_df.csv /app/data/
COPY README.md /app/data/
COPY Sub_Genre_df.csv /app/data/
COPY guidance.txt /app/data/
COPY sample_result.csv /app/data/
