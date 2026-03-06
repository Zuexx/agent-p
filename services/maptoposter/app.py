import glob
import time
import os
import sys
import logging
import traceback
import subprocess
import uuid
import requests
from fastapi import FastAPI, BackgroundTasks, Form

# 配置日誌輸出到 stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI()
DATA_DIR = "/data"
os.makedirs(DATA_DIR, exist_ok=True)
jobs = {}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    city: str = Form(...),
    country: str = Form(...),
    display_city: str = Form(None),
    display_country: str = Form(None),
    font_family: str = Form("Roboto"),
    theme: str = Form("blueprint"),
    callback: str = Form(None)
):
    job_id = str(uuid.uuid4())
    jobs[job_id] = "processing"
    
    logger.info("📥 收到新任務 | Job ID: %s | City: %s, Country: %s", job_id, city, country)
    logger.info("🎨 Theme: %s | Font: %s", theme, font_family)
    logger.info("📞 Callback URL: %s", callback if callback else 'None')
    
    payload = {
        "city": city,
        "country": country,
        "display_city": display_city,
        "display_country": display_country,
        "font_family": font_family,
        "theme": theme,
        "callback": callback
    }
    
    background_tasks.add_task(run_map_generator, job_id, payload)
    
    return {
        "job_id": job_id,
        "status": "processing"
    }

@app.get("/jobs/{job_id}")
def get_status(job_id: str):
    status = jobs.get(job_id, "unknown")
    logger.info("📊 查詢狀態 | Job ID: %s | Status: %s", job_id, status)
    
    output_file = f"{DATA_DIR}/{job_id}.png"
    file_exists = os.path.exists(output_file)
    
    return {
        "job_id": job_id,
        "status": status,
        "file_exists": file_exists
    }

def run_map_generator(job_id, payload):
    logger.info("=" * 80)
    logger.info("🚀 開始處理 | Job ID: %s", job_id)
    logger.info("📍 City: %s, Country: %s", payload["city"], payload["country"])
    logger.info("📞 Callback: %s", payload.get("callback"))
    logger.info("=" * 80)
    
    output_file = f"{DATA_DIR}/{job_id}.png"
    
    # 建構命令
    cmd = [
        "python",
        "create_map_poster.py",
        "--city", payload["city"],
        "--country", payload["country"],
        "--output", output_file
    ]
    
    # 添加可選參數
    if payload.get("display_city"):
        cmd.extend(["--display-city", payload["display_city"]])
    if payload.get("display_country"):
        cmd.extend(["--display-country", payload["display_country"]])
    if payload.get("font_family"):
        cmd.extend(["--font-family", payload["font_family"]])
    if payload.get("theme"):
        cmd.extend(["--theme", payload["theme"]])
    
    logger.info("🎬 執行命令: %s", " ".join(cmd))
    
    try:
        start_time = time.time()
        
        # 在 maptoposter 目錄中執行（解決相對路徑問題）
        result = subprocess.run(
            cmd,
            cwd="/app/maptoposter",
            check=True,
            capture_output=True,
            text=True
        )
        
        elapsed = time.time() - start_time
        
        logger.info("✅ 地圖生成完成 (耗時: %.2f 秒)", elapsed)
        logger.info("📄 輸出文件: %s", output_file)
        
        if result.stdout:
            logger.info("📝 Stdout: %s", result.stdout[:500])
        
        # 清理舊文件
        logger.info("🧹 清理舊的 PNG 文件...")
        cleanup_old_files(directory=DATA_DIR, pattern="*.png", max_age_minutes=10)
        
        jobs[job_id] = "finished"
        
        # 檢查文件大小
        file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
        logger.info("📦 文件大小: %.2f MB", file_size / (1024 * 1024))
        
        # 發送 callback
        callback = payload.get("callback")
        if callback:
            payload_data = {
                "job_id": job_id,
                "status": "finished",
                "elapsed_time": elapsed,
                "file_size": file_size
            }
            
            logger.info("-" * 80)
            logger.info("📤 準備發送 Callback")
            logger.info("   URL: %s", callback)
            logger.info("   Payload: %s", payload_data)
            
            try:
                callback_start = time.time()
                
                with open(output_file, "rb") as f:
                    response = requests.post(
                        callback,
                        data={
                            "job_id": job_id,
                            "status": "finished",
                            "elapsed_time": elapsed,
                            "file_size": file_size
                        },
                        files={
                            "file": (f"{job_id}.png", f, "image/png")
                        },
                        timeout=30
                    )
                
                callback_elapsed = time.time() - callback_start
                
                logger.info("✅ Callback 發送成功!")
                logger.info("   HTTP Status: %s", response.status_code)
                logger.info("   響應時間: %.2f 秒", callback_elapsed)
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
                logger.error("   堆棧追蹤:\n%s", traceback.format_exc())
        else:
            logger.warning("⚠️  沒有提供 Callback URL，跳過通知")
            
    except subprocess.CalledProcessError as e:
        logger.error("❌ 地圖生成失敗")
        logger.error("   Return Code: %s", e.returncode)
        logger.error("   Stderr: %s", e.stderr)
        logger.error("   Stdout: %s", e.stdout)
        jobs[job_id] = "failed"
        
        callback = payload.get("callback")
        if callback:
            logger.info("📤 發送失敗通知...")
            try:
                response = requests.post(
                    callback,
                    json={
                        "job_id": job_id,
                        "status": "failed",
                        "error": e.stderr
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
        logger.error("   堆棧追蹤:\n%s", traceback.format_exc())
        jobs[job_id] = "failed"
        
    finally:
        logger.info("🏁 任務結束 | Job ID: %s | 最終狀態: %s", job_id, jobs.get(job_id, 'unknown'))
        logger.info("=" * 80 + "\n")

def cleanup_old_files(directory: str, pattern: str, max_age_minutes: int = 10):
    """刪除超過指定時間的文件"""
    now = time.time()
    max_age_seconds = max_age_minutes * 60
    
    files = glob.glob(os.path.join(directory, pattern))
    
    for file_path in files:
        try:
            file_age = now - os.path.getctime(file_path)
            if file_age > max_age_seconds:
                os.remove(file_path)
                logger.info("🗑️  已刪除過期文件: %s (存在 %.1f 分鐘)", file_path, file_age/60)
        except Exception as e:
            logger.warning("⚠️  無法刪除 %s: %s", file_path, e)