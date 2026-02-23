#!/usr/bin/env bash
# backend/run.sh
set -e
cd "$(dirname "$0")"
# create artifacts dir
mkdir -p artifacts
# start uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload