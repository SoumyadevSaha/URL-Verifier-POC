# backend/app/orchestrator.py
import os
import time
import json
import socket
import whois
import shutil
from datetime import datetime
from typing import Optional
from sqlmodel import Session, select
from .models import AnalysisJob, JobStatus
from .db import get_session
from .aws_mock import mock_put_artifact
import docker

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARTIFACTS_ROOT = os.path.abspath(os.path.join(BASE, "..", "artifacts"))
SANDBOX_IMAGE = os.environ.get("SANDBOX_IMAGE", "sandbox:local")

class SandboxOrchestrator:
    def __init__(self, artifacts_root: str = ARTIFACTS_ROOT):
        self.client = docker.from_env()
        self.artifacts_root = artifacts_root

    def run_job(self, job_id: str, url: str, timeout: int = 60):
        print(f"[orchestrator] starting job {job_id} for {url}")
        session_engine = self._get_engine()
        # set DB job to running
        with session_engine() as s:
            job = s.get(AnalysisJob, job_id)
            if not job:
                print("[orchestrator] job not found")
                return
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            s.add(job); s.commit()

        # prepare host artifact dir for this job and mount into container
        job_artifact_dir = os.path.join(self.artifacts_root, job_id)
        os.makedirs(job_artifact_dir, exist_ok=True)

        # Run container
        try:
            # run container with limits
            container = self.client.containers.run(
                SANDBOX_IMAGE,
                detach=True,
                environment={"TARGET_URL": url, "JOB_ID": job_id},
                auto_remove=False,  # we'll remove after we collect logs
                volumes={job_artifact_dir: {'bind': '/artifacts', 'mode': 'rw'}},
                network_mode="bridge",
                mem_limit="512m",
                pids_limit=200,
                stderr=True,
                stdout=True,
                cpu_quota=50000  # relative low cpu
            )
            print(f"[orchestrator] container {container.id} started for job {job_id}")

            # stream logs until exit or timeout
            start = time.time()
            logs_accum = b""
            while True:
                logs = container.logs(stdout=True, stderr=True, since=0, stream=False)
                logs_accum = logs
                # check if container has exited
                container.reload()
                if container.status in ("exited", "dead"):
                    break
                if time.time() - start > timeout:
                    print(f"[orchestrator] timeout exceeded for job {job_id}; killing container")
                    container.kill()
                    break
                time.sleep(1)

            # write logs to artifact
            log_path = os.path.join(job_artifact_dir, "worker.log")
            with open(log_path, "wb") as f:
                f.write(logs_accum)

            # try to read result.json written by worker
            result_file = os.path.join(job_artifact_dir, "result.json")
            verdict = "failed"
            summary = "no result"
            risk_score = 0
            if os.path.exists(result_file):
                with open(result_file, "r") as f:
                    r = json.load(f)
                    verdict = r.get("verdict", verdict)
                    summary = r.get("summary", summary)
                    risk_score = r.get("risk_score", risk_score)

            # augment with WHOIS/domain-age check
            domain_age_score = 0
            try:
                w = whois.whois(url)
                # whois module may return dict or object; this is a best-effort extraction
                created = None
                if isinstance(w, dict):
                    created = w.get("creation_date")
                else:
                    created = getattr(w, "creation_date", None)
                # normalize
                if isinstance(created, list):
                    created = created[0]
                if created:
                    age_days = (datetime.utcnow() - created).days
                    if age_days < 7:
                        domain_age_score = 30
                else:
                    domain_age_score = 10
            except Exception as e:
                # whois can fail, leave small penalty
                domain_age_score = 10

            final_score = min(100, (risk_score or 0) + domain_age_score)

            # update DB
            with session_engine() as s:
                job = s.get(AnalysisJob, job_id)
                job.status = JobStatus.SUCCESS if verdict == "malicious" or final_score >= 70 else JobStatus.SUCCESS
                job.finished_at = datetime.utcnow()
                job.verdict = verdict
                job.risk_score = final_score
                job.summary = summary
                s.add(job); s.commit()

            # remove container
            try:
                container.remove(force=True)
            except Exception:
                pass

            print(f"[orchestrator] job {job_id} completed; verdict={verdict} score={final_score}")

        except Exception as e:
            print("orchestrator run exception:", e)
            with session_engine() as s:
                job = s.get(AnalysisJob, job_id)
                job.status = JobStatus.FAILED
                job.finished_at = datetime.utcnow()
                job.summary = f"orchestrator error: {e}"
                s.add(job); s.commit()

    def _get_engine(self):
        # lazy import to avoid circular issues with SQLModel engine creation in main.
        from sqlmodel import Session, create_engine
        DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "jobs.db"))
        engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})
        return lambda : Session(engine)