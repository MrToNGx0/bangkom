import whisper
import threading
import torch

models = {}
lock = threading.Lock()


def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"


def get_model(size="base"):
    device = get_device()

    if size not in models:
        with lock:
            if size not in models:
                print(f"🔄 Loading model: {size} on {device}")
                models[size] = whisper.load_model(size, device=device)

    return models[size]


def transcribe(
    path,
    model_size="base",
    language="auto",
    word_timestamps=True
):
    device = get_device()
    model = get_model(model_size)

    # Improved options for better accuracy
    options = {
        "word_timestamps": word_timestamps,
        "fp16": True if device == "cuda" else False, 
        "beam_size": 5,
        "best_of": 5,
        "no_speech_threshold": 0.6,
        "logprob_threshold": -1.0,
        "condition_on_previous_text": False, # Helps prevent repetitive loops
    }

    if language == "th":
        # Initial prompt helps Whisper understand context and language better
        options["initial_prompt"] = "ภาษาไทย, พูดไทย, Thai language, transcribe correctly."

    if language and language != "auto":
        options["language"] = language

    print(f"🎤 Transcribing | {model_size} | language: {language}")

    return model.transcribe(path, **options)