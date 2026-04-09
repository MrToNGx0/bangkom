from faster_whisper import WhisperModel
import threading
import torch
import os
from app.core import config

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
    vocab_path = os.path.join(config.VOCAB_DIR, "vocab.txt")
    if not os.path.exists(vocab_path):
        return ""
    
    with open(vocab_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    return ", ".join(lines)


def transcribe(
    path,
    model_size="base",
    language="auto",
    word_timestamps=True
):
    model = get_model(model_size)
    
    # Load custom vocabulary for initial prompt
    custom_vocab = load_vocab()
    
    prompt = "ภาษาไทย, พูดไทย, Thai language, transcribe correctly."
    if custom_vocab:
        prompt = f"{prompt} Keywords: {custom_vocab}"

    print(f"🚀 Transcribing with Faster-Whisper | {model_size} | language: {language}")

    # Faster-whisper transcribe returns (segments, info)
    segments_gen, info = model.transcribe(
        path,
        language=None if language == "auto" else language,
        beam_size=5,
        word_timestamps=word_timestamps,
        initial_prompt=prompt,
        condition_on_previous_text=False,
        vad_filter=True,  # Built-in VAD to reduce hallucinations
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    # Convert generator to list of dicts to match previous output format for processor.py
    segments = []
    for s in segments_gen:
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

    return {"segments": segments}
