from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import shutil
import os
import uuid
import json
import asyncio

from app.core import config
from app.services import whisper, processor

router = APIRouter()

# Global dicts for state management
UPLOADED_FILES = {}
CANCEL_REQUESTS = set()


@router.post("/upload")
async def upload(
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="no file uploaded")

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


@router.get("/process/{file_id}")
async def process_stream(
    file_id: str,
    words_per_line: int = 1,
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
            
            for progress, result in transcription_gen:
                if file_id in CANCEL_REQUESTS:
                    print(f"🛑 Cancellation requested for {file_id}")
                    yield f"data: {json.dumps({'status': 'cancelled'})}\n\n"
                    break

                if result is not None:
                    final_result = result
                    break
                
                yield f"data: {json.dumps({'progress': progress})}\n\n"
                await asyncio.sleep(0.05)

            if final_result and file_id not in CANCEL_REQUESTS:
                output_path = processor.process_words(
                    final_result,
                    words_per_line=words_per_line,
                    format_type=format_type,
                    file_id=file_id
                )
                
                if output_path and os.path.exists(output_path):
                    print(f"✅ Success: File created at {output_path}")
                    yield f"data: {json.dumps({'progress': 100, 'download_url': f'/api/download/{file_id}'})}\n\n"
                else:
                    print(f"⚠️ No speech detected or file not created for {file_id}")
                    yield f"data: {json.dumps({'error': 'ไม่พบเสียงที่ต้องการถอดความ หรือเกิดข้อผิดพลาดในการสร้างไฟล์'})}\n\n"
            
            # Cleanup
            if file_id in UPLOADED_FILES:
                del UPLOADED_FILES[file_id]
            if file_id in CANCEL_REQUESTS:
                CANCEL_REQUESTS.remove(file_id)

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ Error during processing: {str(e)}")
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
