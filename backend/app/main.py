# backend/app/main.py
import os
import uuid
import shutil
import threading
import time
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlmodel import Field, SQLModel, create_engine, Session, select
from .models import AnalysisJob, JobStatus
from .schemas import AnalyzeRequest, AnalyzeResponse
from .orchestrator import SandboxOrchestrator
from .db import get_session, init_db
from .aws_mock import mock_put_artifact

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "..", "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app = FastAPI(title="URL Sandbox POC")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

DB_PATH = os.path.join(BASE_DIR, "..", "jobs.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})
init_db(engine)

orchestrator = SandboxOrchestrator(artifacts_root=os.path.abspath(ARTIFACTS_DIR))

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    # create job record
    job_id = str(uuid.uuid4())
    job = AnalysisJob(id=job_id, url=req.url, status=JobStatus.QUEUED)
    with get_session(engine) as session:
        session.add(job)
        session.commit()
    # start job asynchronously
    background_tasks.add_task(orchestrator.run_job, job_id, req.url)
    return AnalyzeResponse(job_id=job_id, status=job.status)

@app.get("/jobs")
def list_jobs():
    with get_session(engine) as session:
        jobs = session.exec(select(AnalysisJob).order_by(AnalysisJob.created_at.desc())).all()
        return jobs

@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    with get_session(engine) as session:
        job = session.get(AnalysisJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

@app.get("/jobs/{job_id}/logs")
def get_logs(job_id: str):
    # try to return combined logs if present
    logs_path = os.path.join(ARTIFACTS_DIR, job_id, "worker.log")
    if not os.path.exists(logs_path):
        raise HTTPException(status_code=404, detail="Logs not found (maybe job still running)")
    return FileResponse(path=logs_path, media_type="text/plain", filename=f"{job_id}-worker.log")

@app.get("/artifacts/{job_id}/{filename}")
def get_artifact(job_id: str, filename: str):
    path = os.path.join(ARTIFACTS_DIR, job_id, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Artifact not found")
    # let the browser download images etc.
    return FileResponse(path=path, filename=filename)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# health
@app.get("/health")
def health():
    return {"status": "ok"}