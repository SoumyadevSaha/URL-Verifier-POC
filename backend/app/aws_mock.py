# backend/app/aws_mock.py
"""
Simple mock for AWS-like artifact storage and metadata store.
Artifacts are just saved under ./artifacts/<job_id>/
This makes migration to S3/DynamoDB straightforward later.
"""
import os
import json

def mock_put_artifact(artifacts_root: str, job_id: str, filename: str, data: bytes):
    folder = os.path.join(artifacts_root, job_id)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(data)
    # write a tiny metadata file
    meta_path = os.path.join(folder, "metadata.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            meta = json.load(f)
    meta.setdefault("files", []).append(filename)
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    return path