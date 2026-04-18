from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
import shutil
import os
import uuid
import json
import asyncio
import time

from app.core import config
from app.services import whisper, processor

router = APIRouter()

# Global dicts for state management
UPLOADED_FILES = {}
CANCEL_REQUESTS = set()


def cleanup_old_files(max_age_seconds=3600 * 24):
    """
    Remove files in input and output directories older than max_age_seconds (default 24h)
    """
    now = time.time()
    for directory in [config.INPUT_DIR, config.OUTPUT_DIR]:
        if not os.path.exists(directory):
            continue
        for f in os.listdir(directory):
            f_path = os.path.join(directory, f)
            # Skip hidden files
            if f.startswith('.'):
                continue
            if os.stat(f_path).st_mtime < now - max_age_seconds:
                try:
                    if os.path.isfile(f_path):
                        os.remove(f_path)
                        print(f"🗑️ Deleted old file: {f}")
                except Exception as e:
                    print(f"⚠️ Failed to delete {f}: {e}")


@router.post("/upload")
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="no file uploaded")

    # Run cleanup in background periodically on each upload
    background_tasks.add_task(cleanup_old_files)

    file_id = str(uuid.uuid4())
    safe_name = "".join([c if c.isalnum() or c in "._-" else "_" for c in file.filename])
    input_path = os.path.join(config.INPUT_DIR, f"{file_id}_{safe_name}")

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    UPLOADED_FILES[file_id] = input_path
    
    return {"file_id": file_id}


@router.post("/cancel/{file_id}")
async def cancel_processing(file_id: str):
    CANCEL_REQUESTS.add(file_id)
    return {"status": "cancel_requested"}


@router.post("/cleanup")
async def manual_cleanup():
    """Endpoint for manual cleanup from UI"""
    cleanup_old_files(max_age_seconds=0) # Delete ALL files
    return {"status": "all_files_deleted"}


@router.get("/process/{file_id}")
async def process_stream(
    file_id: str,
    segment_level: str = "auto",
    format_type: str = "txt",
    model_size: str = "base",
    language: str = "auto"
):
    input_path = UPLOADED_FILES.get(file_id)
    if not input_path:
        raise HTTPException(status_code=404, detail="File not found or already processed")

    if file_id in CANCEL_REQUESTS:
        CANCEL_REQUESTS.remove(file_id)

    async def event_generator():
        try:
            transcription_gen = whisper.transcribe_gen(
                input_path, 
                model_size=model_size, 
                language=language
            )

            final_result = None
            
            for progress, status_text, result in transcription_gen:
                if file_id in CANCEL_REQUESTS:
                    print(f"🛑 Cancellation requested for {file_id}")
                    yield f"data: {json.dumps({'status': 'cancelled'})}\n\n"
                    break

                if result is not None:
                    final_result = result
                    break
                
                yield f"data: {json.dumps({'progress': progress, 'status': status_text})}\n\n"
                await asyncio.sleep(0.01)

            if final_result and file_id not in CANCEL_REQUESTS:
                output_path = processor.process_words(
                    final_result,
                    segment_level=segment_level,
                    format_type=format_type,
                    file_id=file_id
                )
                
                if output_path and os.path.exists(output_path):
                    yield f"data: {json.dumps({'progress': 100, 'status': 'เสร็จสิ้น!', 'download_url': f'/api/download/{file_id}'})}\n\n"
                else:
                    yield f"data: {json.dumps({'error': 'ไม่พบเสียงที่ต้องการถอดความ หรือเกิดข้อผิดพลาดในการสร้างไฟล์'})}\n\n"
            
            # Cleanup
            if file_id in UPLOADED_FILES:
                del UPLOADED_FILES[file_id]
            if file_id in CANCEL_REQUESTS:
                CANCEL_REQUESTS.remove(file_id)

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/download/{file_id}")
def download(file_id: str):
    for f in os.listdir(config.OUTPUT_DIR):
        if f.startswith(file_id):
            return FileResponse(
                os.path.join(config.OUTPUT_DIR, f),
                filename=f,
                media_type="application/octet-stream"
            )

    raise HTTPException(status_code=404, detail="file not found")
