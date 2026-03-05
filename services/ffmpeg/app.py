from fastapi import FastAPI, UploadFile, File, BackgroundTasks
import subprocess
import uuid
import requests
import shutil
import os
import logging
import sys

# 配置日誌輸出到 stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI()
DATA_DIR = "/data"
TMP_DIR = "/tmp"
os.makedirs(DATA_DIR, exist_ok=True)
jobs = {}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    callback: str | None = None
):
    job_id = str(uuid.uuid4())
    jobs[job_id] = "processing"
    input_path = f"{TMP_DIR}/{job_id}_{file.filename}"
    
    logger.info("📥 收到新任務 | Job ID: %s | 檔案: %s", job_id, file.filename)
    logger.info("📞 Callback URL: %s", callback if callback else 'None')
    
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    background_tasks.add_task(run_ffmpeg, job_id, input_path, callback)
    
    return {
        "job_id": job_id,
        "status": "processing"
    }

@app.get("/jobs/{job_id}")
def get_status(job_id: str):
    status = jobs.get(job_id, "unknown")
    logger.info("📊 查詢狀態 | Job ID: %s | Status: %s", job_id, status)
    return {
        "job_id": job_id,
        "status": status
    }

def run_ffmpeg(job_id, input_path, callback):
    logger.info("=" * 80)
    logger.info("🚀 開始處理 | Job ID: %s", job_id)
    logger.info("📁 輸入文件: %s", input_path)
    logger.info("📞 Callback: %s", callback)
    logger.info("=" * 80)
    
    output_file = f"{DATA_DIR}/{job_id}.m4a"
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
    
    try:
        logger.info("🎬 執行 FFmpeg 轉換...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("✅ FFmpeg 轉換完成")
        
        jobs[job_id] = "finished"
        
        # 關鍵：發送 callback
        if callback:
            payload = {
                "job_id": job_id,
                "status": "finished",
                "file": output_file
            }
            
            logger.info("-" * 80)
            logger.info("📤 準備發送 Callback")
            logger.info("   URL: %s", callback)
            logger.info("   Payload: %s", payload)
            
            try:
                import time
                start_time = time.time()
                
                response = requests.post(
                    callback,
                    json=payload,
                    timeout=30,
                    headers={"Content-Type": "application/json"}
                )
                
                elapsed = time.time() - start_time
                
                logger.info("✅ Callback 發送成功!")
                logger.info("   HTTP Status: %s", response.status_code)
                logger.info("   響應時間: %.2f 秒", elapsed)
                logger.info("   響應內容: %s", response.text[:300])
                logger.info("-" * 80)
                
            except requests.exceptions.Timeout as e:
                logger.error("❌ Callback 超時 (30秒)")
                logger.error("   錯誤: %s", e)
            except requests.exceptions.ConnectionError as e:
                logger.error("❌ Callback 連接錯誤")
                logger.error("   錯誤: %s", e)
            except requests.exceptions.RequestException as e:
                logger.error("❌ Callback 請求失敗")
                logger.error("   錯誤類型: %s", type(e).__name__)
                logger.error("   錯誤內容: %s", e)
            except Exception as e:
                logger.error("❌ Callback 發送時發生未知錯誤")
                logger.error("   錯誤類型: %s", type(e).__name__)
                logger.error("   錯誤內容: %s", e)
                import traceback
                logger.error("   堆棧追蹤:\n%s", traceback.format_exc())
        else:
            logger.warning("⚠️  沒有提供 Callback URL，跳過通知")
            
    except subprocess.CalledProcessError as e:
        logger.error("❌ FFmpeg 處理失敗")
        logger.error("   Return Code: %s", e.returncode)
        logger.error("   Stderr: %s", e.stderr)
        jobs[job_id] = "failed"
        
        if callback:
            logger.info("📤 發送失敗通知...")
            try:
                response = requests.post(
                    callback,
                    json={
                        "job_id": job_id,
                        "status": "failed",
                        "error": str(e)
                    },
                    timeout=10
                )
                logger.info("✅ 失敗通知已發送 (Status: %s)", response.status_code)
            except Exception as cb_error:
                logger.error("❌ 發送失敗通知也失敗: %s", cb_error)
                
    except Exception as e:
        logger.error("❌ 處理過程中發生未知錯誤")
        logger.error("   錯誤類型: %s", type(e).__name__)
        logger.error("   錯誤內容: %s", e)
        import traceback
        logger.error("   堆棧追蹤:\n%s", traceback.format_exc())
        jobs[job_id] = "failed"
        
    finally:
        # 清理臨時文件
        if os.path.exists(input_path):
            os.remove(input_path)
            logger.info("🧹 已清理臨時文件: %s", input_path)
        
        logger.info("🏁 任務結束 | Job ID: %s | 最終狀態: %s", job_id, jobs.get(job_id, 'unknown'))
        logger.info("=" * 80 + "\n")