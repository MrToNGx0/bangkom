from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import shutil
import os
import uuid

from app.whisper_engine import transcribe
from app.processor import process_words

app = FastAPI()

ROOT_DIR = os.getcwd()

STATIC_DIR = os.path.join(ROOT_DIR, "web")
INPUT_DIR = os.path.join(ROOT_DIR, "input")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root():
    index_path = os.path.join(STATIC_DIR, "index.html")

    if not os.path.exists(index_path):
        raise HTTPException(status_code=500, detail=f"index.html not found at {index_path}")

    return FileResponse(index_path)


@app.post("/upload")
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

    if model_size not in ["base", "small", "medium"]:
        model_size = "base"

    if language not in ["auto", "th", "en", "ja", "zh"]:
        language = "auto"

    file_id = str(uuid.uuid4())
    safe_name = file.filename.replace(" ", "_")
    input_path = os.path.join(INPUT_DIR, f"{file_id}_{safe_name}")

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = transcribe(input_path, model_size, language)

    output_path = process_words(
        result,
        words_per_line=words_per_line,
        format_type=format_type,
        file_id=file_id
    )

    return {
        "file_id": file_id,
        "download_url": f"/download/{file_id}"
    }


@app.get("/download/{file_id}")
def download(file_id: str):
    for f in os.listdir(OUTPUT_DIR):
        if f.startswith(file_id):
            return FileResponse(
                os.path.join(OUTPUT_DIR, f),
                filename=f,
                media_type="application/octet-stream"
            )

    raise HTTPException(status_code=404, detail="file not found")