from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import shutil
import os
import uuid

from app.core import config
from app.services import whisper, processor

router = APIRouter()


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    words_per_line: int = Form(1),
    format_type: str = Form("txt"),
    model_size: str = Form("base"),
    language: str = Form("auto")
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="no file uploaded")

    if format_type not in ["txt", "srt"]:
        raise HTTPException(status_code=400, detail="invalid format")

    if model_size not in config.ALLOWED_MODELS:
        model_size = config.DEFAULT_MODEL

    if language not in config.ALLOWED_LANGUAGES:
        language = "auto"

    file_id = str(uuid.uuid4())
    safe_name = "".join([c if c.isalnum() or c in "._-" else "_" for c in file.filename])
    input_path = os.path.join(config.INPUT_DIR, f"{file_id}_{safe_name}")

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = whisper.transcribe(input_path, model_size, language)

        output_path = processor.process_words(
            result,
            words_per_line=words_per_line,
            format_type=format_type,
            file_id=file_id
        )

        return {
            "file_id": file_id,
            "download_url": f"/api/download/{file_id}"
        }
    except Exception as e:
        print(f"❌ Error during transcription: {str(e)}")
        raise HTTPException(status_code=500, detail="Processing failed")


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
