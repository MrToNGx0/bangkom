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
    model = get_model(model_size)

    options = {
        "word_timestamps": word_timestamps,
        "fp16": False  # CPU safe
    }

    if language and language != "auto":
        options["language"] = language

    print(f"🎤 Transcribing | {model_size}")

    return model.transcribe(path, **options)