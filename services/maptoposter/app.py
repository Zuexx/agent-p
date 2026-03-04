from fastapi import FastAPI, BackgroundTasks
import subprocess
import uuid
import requests
import os

app = FastAPI()
jobs = {}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jobs")
def create_job(payload: dict, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = "processing"

    background_tasks.add_task(run_job, job_id, payload)

    return {"job_id": job_id, "status": "processing"}

def run_job(job_id, payload):
    city = payload["city"]
    country = payload["country"]
    callback = payload.get("callback")

    output_file = f"/data/{job_id}.png"

    cmd = [
        "python",
        "/app/maptoposter/create_map_poster.py",
        "--city", city,
        "--country", country,
        "--output", output_file
    ]

    subprocess.run(cmd)

    jobs[job_id] = "finished"

    if callback:
        requests.post(callback, json={
            "job_id": job_id,
            "status": "finished",
            "file": output_file
        })