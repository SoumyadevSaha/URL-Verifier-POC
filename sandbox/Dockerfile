# sandbox/Dockerfile
FROM python:3.11-slim

# basic deps
RUN apt-get update && apt-get install -y \
    wget curl gnupg ca-certificates libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxss1 libasound2 libx11-xcb1 libxcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libgtk-3-0 xvfb --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy worker
COPY worker.py /app/worker.py
COPY entrypoint.sh /app/entrypoint.sh
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# install playwright browsers
RUN python -m playwright install --with-deps

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]