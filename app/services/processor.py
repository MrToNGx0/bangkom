import os
import re
from app.core import config

try:
    from pythainlp.tokenize import word_tokenize
except ImportError:
    # Fallback if pythainlp is not installed yet
    def word_tokenize(text):
        return [text]

def is_thai(text):
    return bool(re.search('[\u0e00-\u0e7f]', text))

def format_time(t):
    return f"{int(t//3600):02}:{int((t%3600)//60):02}:{int(t%60):02},{int((t%1)*1000):03}"

def join_words(buffer):
    res = ""
    for i, w in enumerate(buffer):
        if i > 0:
            if not is_thai(buffer[i-1]) or not is_thai(w):
                res += " "
        res += w
    return res

def clean_text(text):
    text = text.strip()
    if is_thai(text):
        text = text.rstrip(',')
    
    if text.lower() in ['i', '.', ',', '!', '?']:
        return ""
    return text

def split_thai_words_with_timing(merged_words):
    """
    If words_per_line is 1 and a 'word' contains multiple Thai words, 
    split them using pythainlp and interpolate timings.
    """
    new_words = []
    for w in merged_words:
        text = w["word"]
        # If it's Thai and looks like a long phrase (multiple words)
        if is_thai(text) and len(text) > 4:
            tokens = word_tokenize(text, engine="newmm")
            # Remove any empty tokens or purely punctuation tokens
            tokens = [t.strip() for t in tokens if t.strip() and t.strip() not in [',', '.', '!', '?']]
            
            if len(tokens) > 1:
                duration = w["end"] - w["start"]
                token_duration = duration / len(tokens)
                
                for idx, t in enumerate(tokens):
                    new_words.append({
                        "word": t,
                        "start": w["start"] + (idx * token_duration),
                        "end": w["start"] + ((idx + 1) * token_duration)
                    })
                continue
        
        new_words.append(w)
    return new_words

def merge_thai_tokens(raw_words):
    if not raw_words:
        return []
    
    merged = []
    current = None
    
    # Marks that MUST be attached to previous (Vowels/Tones/Marks)
    thai_marks = r'[\u0e30-\u0e3a\u0e47-\u0e4e\u0e31]' 
    
    for w in raw_words:
        word_text = w["word"]
        clean_w = clean_text(word_text)
        if not clean_w and word_text.strip():
            continue
            
        starts_with_space = word_text.startswith(" ")
        is_mark_only = len(clean_w) == 1 and bool(re.match(thai_marks, clean_w))
        is_fragment = len(clean_w) == 1 and not starts_with_space
        
        if current and (is_mark_only or (is_fragment and is_thai(current["word"][-1]) and is_thai(clean_w))):
            current["word"] += clean_w
            current["end"] = max(current["end"], w["end"])
        else:
            if current:
                merged.append(current)
            current = {
                "word": clean_w,
                "start": w["start"],
                "end": w["end"]
            }
            
    if current:
        merged.append(current)
        
    return [m for m in merged if m["word"]]

def process_words(result, words_per_line=1, format_type="txt", file_id="output"):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(config.OUTPUT_DIR, f"{file_id}.{format_type}")

    raw_words = []
    for seg in result["segments"]:
        for w in seg["words"]:
            raw_words.append(w)

    if not raw_words:
        return ""

    # 1. First merge characters into tokens (Whisper level)
    words = merge_thai_tokens(raw_words)
    
    # 2. If 1 word per line, split phrases into actual Thai words (PyThaiNLP level)
    if words_per_line == 1:
        words = split_thai_words_with_timing(words)

    if format_type == "txt":
        with open(output_file, "w", encoding="utf-8") as f:
            buffer = []
            for w in words:
                buffer.append(w["word"])
                if len(buffer) >= words_per_line:
                    f.write(join_words(buffer) + "\n")
                    buffer = []
            if buffer:
                f.write(join_words(buffer) + "\n")

    elif format_type == "srt":
        with open(output_file, "w", encoding="utf-8") as f:
            idx = 1
            for i in range(0, len(words), words_per_line):
                chunk = words[i : i + words_per_line]
                if not chunk: continue
                
                start = chunk[0]["start"]
                end = chunk[-1]["end"]
                
                if words_per_line == 1 and i < len(words) - 1:
                    next_start = words[i+1]["start"]
                    if next_start - end < 0.3:
                        end = next_start
                
                if end <= start:
                    end = start + 0.1
                
                text = join_words([w["word"] for w in chunk])
                
                f.write(f"{idx}\n")
                f.write(f"{format_time(start)} --> {format_time(end)}\n")
                f.write(f"{text}\n\n")
                idx += 1

    return output_file
