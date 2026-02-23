# URL Sandbox POC – Dynamic Malicious URL Analysis System

## Overview

This project implements a **local Proof-of-Concept (POC) dynamic URL detonation sandbox** using:

- **FastAPI** – API server and UI
- **SQLite (SQLModel)** – Local database
- **Docker SDK (Python)** – Container orchestration
- **Playwright (Chromium)** – Headless browser sandbox
- **Local artifact storage (AWS-mock layer)** – For future S3/Dynamo migration
- **Isolated per-URL container execution**
- **Explainable risk scoring system**

The system accepts a URL, spins up an isolated Docker container, runs the URL inside a headless Chromium browser, collects artifacts, detects suspicious behavior, calculates a risk score, generates an explainable result, and destroys the container.

This POC is designed for:
- Academic projects
- Security research
- Malware analysis experiments
- Understanding sandbox architecture
- Future migration to AWS ECS/Fargate

---

# Table of Contents

1. Architecture Overview
2. Full Project Structure
3. System Design Concepts
4. Installation Requirements
5. Complete Setup Guide
6. How the System Works (End-to-End Flow)
7. API Documentation
8. UI Usage Guide
9. Risk Scoring Logic
10. Artifact Storage
11. Security & Isolation Model
12. Monitoring & Logs
13. Database Schema
14. Migration to AWS (Design Strategy)
15. Troubleshooting
16. Limitations
17. Future Improvements

---

# 1. Architecture Overview

## High-Level Flow

```
User → FastAPI Backend → Orchestrator → Docker Sandbox Worker
                                      ↓
                                Artifact Storage
                                      ↓
                                 SQLite DB
                                      ↓
                                   UI / API
```

Each URL:
- Runs in a **dedicated container**
- Has resource limits
- Has timeouts
- Is destroyed after completion
- Leaves behind artifacts and explainable report

---

# 2. Full Project Structure

```
url-sandbox-poc/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── orchestrator.py
│   │   ├── aws_mock.py
│   │   ├── templates/
│   │   │   └── index.html
│   │   └── static/
│   │       └── ui.js
│   ├── requirements.txt
│   └── run.sh
│
├── sandbox/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── worker.py
│   └── requirements.txt
│
├── artifacts/
├── jobs.db
└── README.md
```

---

# 3. System Design Concepts

## Core Components

### Backend (FastAPI)
- Accepts URL
- Creates job
- Launches Docker container
- Monitors execution
- Stores results
- Provides UI and APIs

### Orchestrator
- Uses Docker SDK
- Enforces:
  - CPU limits
  - Memory limits
  - PID limits
  - Timeout
- Collects logs
- Destroys container

### Sandbox Worker (Playwright)
- Launches Chromium
- Injects JS hooks
- Captures:
  - DOM
  - Screenshot
  - Network requests
  - Console logs
  - Downloads
- Detects:
  - getUserMedia usage
  - eval() usage
  - document.write
  - suspicious file downloads

### AWS Mock Layer
- Simulates S3 storage locally
- Makes migration to cloud trivial

---

# 4. Installation Requirements

## Required

- Linux system
- Python 3.11+
- Docker installed and running
- Internet access (for browser fetch)

---

## Install Docker (if needed)

Ubuntu example:

```bash
sudo apt update
sudo apt install docker.io
sudo systemctl start docker
sudo usermod -aG docker $USER
```

Log out and log back in.

Test:

```bash
docker ps
```

---

# 5. Complete Setup Guide

## Step 1 – Clone or Create Project

Create folder:

```bash
mkdir url-sandbox-poc
cd url-sandbox-poc
```

Create the file structure exactly as shown above and paste all code files provided earlier.

---

## Step 2 – Setup Backend Environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 3 – Build Sandbox Image

```bash
cd ../sandbox
chmod +x entrypoint.sh
docker build -t sandbox:local .
```

This installs Playwright and Chromium inside the container.

---

## Step 4 – Start Backend

```bash
cd ../backend
chmod +x run.sh
./run.sh
```

Server runs at:

```
http://localhost:8000
```

---

# 6. How the System Works (End-to-End Flow)

### Step 1
User submits URL via:
- UI
- POST `/analyze`

### Step 2
Backend:
- Generates UUID
- Saves job to SQLite
- Calls `orchestrator.run_job()` in background

### Step 3
Orchestrator:
- Creates artifact directory
- Starts container:
  - `sandbox:local`
  - Mounts `/artifacts`
  - Applies memory + CPU limits
- Waits for container exit or timeout
- Collects logs
- Reads `result.json`
- Applies WHOIS scoring
- Updates DB
- Removes container

### Step 4
Worker:
- Launches headless Chromium
- Injects JS detection hooks
- Navigates to URL
- Waits 3 seconds
- Captures artifacts
- Computes risk score
- Writes `result.json`
- Exits

### Step 5
UI updates automatically.

---

# 7. API Documentation

## POST /analyze

Request:

```json
{
  "url": "https://example.com"
}
```

Response:

```json
{
  "job_id": "uuid",
  "status": "queued"
}
```

---

## GET /jobs

Returns all jobs.

---

## GET /jobs/{job_id}

Returns job details.

---

## GET /jobs/{job_id}/logs

Returns container logs.

---

## GET /artifacts/{job_id}/{filename}

Returns artifact file.

---

# 8. UI Usage

Visit:

```
http://localhost:8000
```

Features:
- Submit URL
- View status
- View logs
- View screenshot
- View artifacts

Auto-refresh every 3 seconds.

---

# 9. Risk Scoring Logic

Inside worker:

| Behavior | Score |
|----------|--------|
| getUserMedia | +30 |
| eval() usage | +20 |
| suspicious download | +40 |
| many network calls | +5 |

Verdict:
- ≥70 → malicious
- 40–69 → suspicious
- <40 → benign

Orchestrator adds domain-age penalty.

Final score capped at 100.

---

# 10. Artifact Storage

Artifacts per job:

```
artifacts/<job_id>/
├── dom.html
├── screenshot.png
├── network.json
├── console.json
├── downloads.json
├── result.json
└── worker.log
```

---

# 11. Security & Isolation Model

Container restrictions:
- 512MB memory
- Limited CPU quota
- PID limit
- Timeout (60s)
- No privileged mode
- No host mounts except artifacts folder

⚠️ WARNING:
This is not production-grade isolation.
Do NOT test dangerous malware on personal systems.

---

# 12. Monitoring & Logs

### View Docker containers:

```bash
docker ps
```

### View running logs:

```bash
docker logs <container_id>
```

### View backend logs:
Shown in terminal running `run.sh`.

---

# 13. Database Schema

SQLite `jobs.db`

Table: `analysisjob`

Fields:
- id
- url
- status
- created_at
- started_at
- finished_at
- verdict
- risk_score
- summary

---

# 14. Migration to AWS

Replace:

| Local | AWS |
|--------|-----|
| SQLite | DynamoDB / RDS |
| ./artifacts | S3 |
| Docker SDK | ECS RunTask |
| Local host | Fargate |
| BackgroundTasks | SQS + Lambda |

Minimal code changes required.

---

# 15. Troubleshooting

## Docker permission error

Add user to docker group:

```bash
sudo usermod -aG docker $USER
```

---

## Playwright fails

Rebuild image:

```bash
docker build --no-cache -t sandbox:local .
```

---

## Worker timeout

Increase timeout in `orchestrator.py`.

---

# 16. Limitations

- No anti-evasion stealth
- No TLS interception
- No advanced malware unpacking
- No proxy support
- No traffic decryption
- Basic scoring only
- Single-node system

---

# 17. Future Improvements

- Firecracker microVM
- gVisor
- ML-based DOM anomaly detection
- LLM phishing detection
- HAR file capture
- DNS analysis
- IP reputation APIs
- Redis queue
- Kubernetes Jobs
- Distributed workers
- Real-time streaming logs
- Behavioral graph modeling

---

<!-- # Conclusion

This project demonstrates a complete:

- Dynamic URL sandbox
- Container orchestration pipeline
- Explainable risk engine
- Artifact collection system
- Local UI
- Cloud-ready design

It is fully runnable locally and architected for future AWS migration.

--- -->