from faster_whisper import WhisperModel
import threading
import torch
import os
from app.core import config
from app.core.database import SessionLocal
from app.models.db_models import Vocab

models = {}
lock = threading.Lock()


def get_device():
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def get_model(size="base"):
    device = get_device()
    compute_type = "float16" if device == "cuda" else "int8"

    if size not in models:
        with lock:
            if size not in models:
                print(f"🔄 Loading Faster-Whisper: {size} on {device} ({compute_type})")
                models[size] = WhisperModel(size, device=device, compute_type=compute_type)

    return models[size]


def load_vocab():
    db = SessionLocal()
    try:
        items = db.query(Vocab).all()
        if not items:
            return ""
        return ", ".join([i.word for i in items])
    finally:
        db.close()


def transcribe_gen(
    path,
    model_size="base",
    language="auto",
    word_timestamps=True
):
    """
    Generator version of transcribe to report progress with status
    Yields: (progress, status_message, result)
    """
    yield 10, "กำลังโหลดโมเดล AI...", None
    model = get_model(model_size)
    
    custom_vocab = load_vocab()
    prompt = "นี่คือเสียงภาษาไทย ถอดความทุกคำพูดอย่างถูกต้อง แม่นยำ และครบถ้วน"
    if custom_vocab:
        prompt = f"{prompt} Keywords: {custom_vocab}"

    yield 15, "กำลังเตรียมไฟล์เสียง...", None

    segments_gen, info = model.transcribe(
        path,
        language=None if language == "auto" else language,
        beam_size=10,
        word_timestamps=word_timestamps,
        initial_prompt=prompt,
        condition_on_previous_text=False,
        repetition_penalty=1.2,
        no_repeat_ngram_size=3,
        no_speech_threshold=0.5,
        vad_filter=True,
        # ปรับค่า VAD ให้ไวขึ้น (หูไวขึ้น) และแถมเวลาช่วงเริ่มให้มากขึ้น
        # threshold: ลดลงเพื่อให้ดักเสียงเบาๆ ตอนเริ่มได้ (0.5 -> 0.3)
        # speech_pad_ms: เพิ่มจาก 200 เป็น 400 เพื่อให้ซับขึ้นมารอก่อนพูดเล็กน้อย
        vad_parameters=dict(
            min_silence_duration_ms=300,
            speech_pad_ms=400,
            threshold=0.3
        ),
    )

    total_duration = info.duration
    segments = []

    # Transcription phase: 20% to 90%
    for s in segments_gen:
        # Calculate progress within the 20-90 range
        audio_progress = s.end / total_duration
        p = 20 + int(audio_progress * 70)
        p = min(p, 90)
        
        status = f"กำลังถอดความ... {int(s.end)} / {int(total_duration)} วินาที"
        
        seg_dict = {
            "start": s.start,
            "end": s.end,
            "text": s.text,
            "words": []
        }
        if s.words:
            for w in s.words:
                seg_dict["words"].append({
                    "start": w.start,
                    "end": w.end,
                    "word": w.word
                })
        
        segments.append(seg_dict)
        yield p, status, None

    # Final result
    yield 95, "กำลังจัดรูปแบบภาษาไทย...", {"segments": segments}
