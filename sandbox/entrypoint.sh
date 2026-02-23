#!/usr/bin/env bash
set -e
echo "[worker] entrypoint starting"
# run worker (it will read TARGET_URL and JOB_ID from env)
python /app/worker.py