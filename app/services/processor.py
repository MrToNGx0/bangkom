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

def load_hallucinations():
    h_path = os.path.join(config.VOCAB_DIR, "hallucinations.txt")
    if not os.path.exists(h_path):
        return []
    with open(h_path, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip() and not line.startswith("#")]

# Cache hallucinations list
HALLUCINATIONS = load_hallucinations()

def format_time(t):
    return f"{int(t//3600):02}:{int((t%3600)//60):02}:{int(t%60):02},{int((t%1)*1000):03}"

def clean_text(text):
    text = text.strip()
    if not text:
        return ""
        
    if is_thai(text):
        # Remove common Whisper Thai hallucinations
        text = text.rstrip(',').rstrip('.')
    
    clean_low = text.lower()
    for h in HALLUCINATIONS:
        if h in clean_low and len(text) < len(h) + 5:
            return ""

    if text.lower() in ['i', '.', ',', '!', '?', '(', ')', '[', ']']:
        return ""
    return text

def filter_repetitions(words):
    """
    Remove excessive word repetitions that often occur during noise or silence.
    """
    if len(words) < 3:
        return words
        
    filtered = []
    i = 0
    while i < len(words):
        # ตรวจสอบการซ้ำกัน 3 ครั้งติดกัน (เช่น "ครับ ครับ ครับ")
        if i < len(words) - 2:
            w1 = words[i]["word"].strip().lower()
            w2 = words[i+1]["word"].strip().lower()
            w3 = words[i+2]["word"].strip().lower()
            
            if w1 == w2 == w3 and is_thai(w1) and len(w1) > 0:
                # ถ้าซ้ำ 3 ครั้ง ให้เก็บไว้แค่ 1 และข้ามที่เหลือ
                filtered.append(words[i])
                i += 3
                continue
        
        filtered.append(words[i])
        i += 1
    return filtered

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
                
                # ปรับให้มีช่องว่างเล็กน้อยระหว่างคำในประโยคเดียวกัน (0.01s) เพื่อไม่ให้คำติดกันเกินไป
                # แต่ยังคงความเป๊ะของช่วงเวลา
                current_start = w["start"]
                for i, t in enumerate(tokens):
                    t_duration = (len(t) / total_chars) * duration
                    
                    t_end = current_start + t_duration
                    
                    # ลดความยาวคำสุดท้ายลงเล็กน้อยถ้าไม่ใช่คำเดียวโดดๆ เพื่อให้เห็นช่องว่างใน Timeline
                    actual_end = t_end
                    if i < len(tokens) - 1:
                        actual_end -= 0.01 

                    new_words.append({
                        "word": t,
                        "start": current_start,
                        "end": max(current_start + 0.05, actual_end)
                    })
                    current_start += t_duration
                continue
        
        new_words.append(w)
    return new_words

def merge_thai_tokens(raw_words):
    """
    Carefully merge Thai tokens that are likely fragments of the same word,
    while preserving timing for distinct words.
    """
    if not raw_words:
        return []
    
    merged = []
    current = None
    
    for w in raw_words:
        word_text = w["word"]
        # Whisper Thai often has leading spaces for new words/phrases
        has_leading_space = word_text.startswith(" ")
        clean_w = clean_text(word_text)
        
        if not clean_w and word_text.strip():
            continue
            
        should_merge = False
        if current:
            gap = w["start"] - current["end"]
            
            # 1. Merge if it's a known combining mark or fragment (no space and very close)
            # Thai combining marks often appear as separate tokens in Whisper
            is_fragment = not has_leading_space and gap < 0.1
            
            # 2. Merge if the gap is extremely small (likely same word split by AI)
            is_tight = gap < 0.05
            
            if is_thai(current["word"][-1]) and is_thai(clean_w):
                if is_tight or is_fragment:
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
    
    # 2. Filter hallucinations and repetitions
    words = filter_repetitions(words)
    
    # 3. If 1 word per line, split those solid phrases into actual linguistic words
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
                
                if end <= start:
                    end = start + 0.1
                
                text = join_words([w["word"] for w in chunk])
                
                f.write(f"{idx}\n")
                f.write(f"{format_time(start)} --> {format_time(end)}\n")
                f.write(f"{text}\n\n")
                idx += 1

    return output_file
