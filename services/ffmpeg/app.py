from fastapi import FastAPI, BackgroundTasks
import subprocess
import uuid
import requests

app = FastAPI()
jobs = {}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jobs")
def create_job(payload: dict, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = "processing"

    background_tasks.add_task(run_ffmpeg, job_id, payload)

    return {"job_id": job_id, "status": "processing"}

def run_ffmpeg(job_id, payload):
    input_file = payload["input"]
    callback = payload.get("callback")

    output_file = f"/data/{job_id}.m4a"

    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-movflags", "+faststart",
        output_file,
        "-y"
    ]

    subprocess.run(cmd)

    jobs[job_id] = "finished"

    if callback:
        requests.post(callback, json={
            "job_id": job_id,
            "status": "finished",
            "file": output_file
        })