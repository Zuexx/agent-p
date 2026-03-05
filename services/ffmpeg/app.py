from fastapi import FastAPI, UploadFile, File, BackgroundTasks
import subprocess
import uuid
import requests
import shutil
import os

app = FastAPI()
jobs = {}
@app.get("/health") 
def health(): 
    return {"status": "ok"}

@app.post("/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    callback: str = None
):
    job_id = str(uuid.uuid4())
    jobs[job_id] = "processing"

    input_path = f"/tmp/{job_id}_{file.filename}"

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    background_tasks.add_task(run_ffmpeg, job_id, input_path, callback)

    return {"job_id": job_id, "status": "processing"}


def run_ffmpeg(job_id, input_path, callback):
    output_file = f"/data/{job_id}.m4a"

    cmd = [
        "ffmpeg",
        "-i", input_path,
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
            "status": "finished"
        })