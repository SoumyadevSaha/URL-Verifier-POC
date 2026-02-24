How to set this up and run (step-by-step)

Prereqs

Linux host

Docker (install & start)

Python 3.11+ and pip

Add your user to the docker group or use sudo when required

Clone project tree

Create the directory structure shown earlier and paste files.

Create and activate Python venv for backend

cd url-sandbox-poc/backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

Install Playwright deps for host (not required for worker container but helpful for quick local tests)

python -m pip install playwright
python -m playwright install

Build sandbox docker image

cd ../sandbox
# ensure entrypoint.sh is executable
chmod +x entrypoint.sh
docker build -t sandbox:local .

If Docker build fails due to missing system packages, update the Debian package list or ensure your machine has required libs.

Start backend

cd ../backend
# ensure run.sh is executable
chmod +x run.sh
./run.sh

This starts FastAPI on http://0.0.0.0:8000. Open that in your browser.

Use the UI

In your browser go to http://localhost:8000

Enter a URL (e.g., https://example.com) and click Analyze

Watch the jobs list update. Click logs or artifacts to view results.

Where artifacts go

Artifacts are under url-sandbox-poc/artifacts/<job_id>/:

dom.html, screenshot.png, network.json, console.json, result.json, worker.log

How this maps to AWS (so migration is easy later)

mock_put_artifact writes to ./artifacts/ — swap to upload to S3 once on AWS. (Small change)

SQLite + SQLModel can be replaced with DynamoDB or RDS — schema kept simple to ease migration.

Docker workers can be replaced by Fargate/EKS jobs — orchestrator code that calls Docker SDK becomes an AWS ECS / EKS submitter.

whois and intelligence layers can be replaced with dedicated API calls (VirusTotal, Google Safe Browsing, AbuseIP).

Improvements & Production Hardening (next steps you can implement)

Run workers inside microVMs (Firecracker) or gVisor for stronger isolation.

Use private egress proxies and strict network ACLs to control external access.

Implement HAR generation and TLS interception for deeper inspection.

Use provable infrastructure for timeouts and job retries (k8s Jobs or ECS RunTask).

Implement rate-limiting, input sanitization, and queueing (SQS / RabbitMQ) to avoid DoS from many jobs.

Quick troubleshooting

If worker container fails with Playwright browser errors: ensure the playwright install step in Dockerfile ran successfully (the Dockerfile runs python -m playwright install --with-deps). You can run a test container interactively:

docker run -it --rm sandbox:local /bin/bash
python -c "from playwright.sync_api import sync_playwright; print('ok')"

If Docker permission errors occur, run commands with sudo or add your user to docker group.