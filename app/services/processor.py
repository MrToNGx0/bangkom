import os
import re
from app.core import config

try:
    from pythainlp.tokenize import word_tokenize
except ImportError:
    def word_tokenize(text, engine="newmm"):
        return [text]

def is_thai(text):
    return bool(re.search('[\u0e00-\u0e7f]', text))

def format_time(t):
    return f"{int(t//3600):02}:{int((t%3600)//60):02}:{int(t%60):02},{int((t%1)*1000):03}"

def clean_text(text):
    text = text.strip()
    if is_thai(text):
        # Remove common Whisper Thai hallucinations
        text = text.rstrip(',').rstrip('.')
    
    if text.lower() in ['i', '.', ',', '!', '?']:
        return ""
    return text

def split_thai_words_with_timing(merged_words):
    """
    Split long Thai phrases into individual words using character-length based timing.
    """
    new_words = []
    for w in merged_words:
        text = w["word"]
        # If it's Thai and not a very short word
        if is_thai(text) and len(text) > 1:
            tokens = word_tokenize(text, engine="newmm")
            # Filter empty/junk tokens
            tokens = [t.strip() for t in tokens if t.strip() and t.strip() not in [',', '.', '!', '?']]
            
            if len(tokens) > 1:
                total_chars = sum(len(t) for t in tokens)
                duration = w["end"] - w["start"]
                
                current_start = w["start"]
                for t in tokens:
                    # Distribute time based on character length ratio
                    t_duration = (len(t) / total_chars) * duration
                    new_words.append({
                        "word": t,
                        "start": current_start,
                        "end": current_start + t_duration
                    })
                    current_start += t_duration
                continue
        
        new_words.append(w)
    return new_words

def merge_thai_tokens(raw_words):
    """
    Aggressively merge Thai tokens that are close to each other, 
    ignoring Whisper's guessed spaces.
    """
    if not raw_words:
        return []
    
    merged = []
    current = None
    
    for w in raw_words:
        word_text = w["word"]
        clean_w = clean_text(word_text)
        
        if not clean_w and word_text.strip():
            continue
            
        should_merge = False
        if current:
            # If both are Thai and the gap is very small (< 0.3s)
            # we merge them regardless of spaces because Thai has no spaces.
            gap = w["start"] - current["end"]
            if is_thai(current["word"][-1]) and is_thai(clean_w) and gap < 0.3:
                should_merge = True
            # Also merge if it's a known combining mark/fragment (no space at start)
            elif not word_text.startswith(" ") and is_thai(current["word"][-1]) and is_thai(clean_w):
                should_merge = True
        
        if should_merge:
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

def join_words(buffer):
    res = ""
    for i, w in enumerate(buffer):
        if i > 0:
            # Add space only if moving between languages
            if not is_thai(buffer[i-1]) or not is_thai(w):
                res += " "
        res += w
    return res

def process_words(result, words_per_line=1, format_type="txt", file_id="output"):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(config.OUTPUT_DIR, f"{file_id}.{format_type}")

    raw_words = []
    for seg in result["segments"]:
        for w in seg["words"]:
            raw_words.append(w)

    if not raw_words:
        return ""

    # 1. Merge Thai fragments into solid phrases
    words = merge_thai_tokens(raw_words)
    
    # 2. If 1 word per line, split those solid phrases into actual linguistic words
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
                
                # Smoother timing (Gapless)
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
