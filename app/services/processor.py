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

def split_long_segment(text, start, end, max_chars=40, max_duration=6.0):
    """
    Splits a single long segment into multiple smaller ones 
    based on character length and duration.
    """
    duration = end - start
    if duration <= max_duration and len(text) <= max_chars:
        return [{"text": text, "start": start, "end": end}]
    
    # Simple split by duration/length ratio
    tokens = word_tokenize(text)
    # Filter empty
    tokens = [t for t in tokens if t.strip()]
    
    if not tokens:
        return []
        
    segments = []
    current_tokens = []
    current_start = start
    
    total_chars = sum(len(t) for t in tokens)
    processed_chars = 0
    
    for i, t in enumerate(tokens):
        current_tokens.append(t)
        processed_chars += len(t)
        
        current_text = "".join(current_tokens)
        current_duration = (processed_chars / total_chars) * duration
        
        # Split if exceeds chars or duration
        if len(current_text) >= max_chars or current_duration >= max_duration:
            segments.append({
                "text": current_text,
                "start": current_start,
                "end": current_start + current_duration
            })
            current_start += current_duration
            current_tokens = []
            
    if current_tokens:
        segments.append({
            "text": "".join(current_tokens),
            "start": current_start,
            "end": end
        })
        
    return segments

def process_words(result, segment_level="auto", format_type="txt", file_id="output"):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(config.OUTPUT_DIR, f"{file_id}.{format_type}")

    MAX_DUR = 6.0 # Maximum seconds a subtitle should stay
    MAX_CHARS = 45 # Maximum characters per line for professional look

    processed_segments = []

    if segment_level == "auto":
        # Use Whisper segments but apply professional splitting
        for seg in result["segments"]:
            clean_seg_text = clean_text(seg["text"])
            if not clean_seg_text:
                continue
            
            # Split if original segment is too long
            splits = split_long_segment(
                clean_seg_text, 
                seg["start"], 
                seg["end"], 
                max_chars=MAX_CHARS,
                max_duration=MAX_DUR
            )
            processed_segments.extend(splits)
    else:
        # Flatten and re-group
        raw_words = []
        for seg in result["segments"]:
            for w in seg["words"]:
                raw_words.append(w)

        if not raw_words:
            return ""

        words = merge_thai_tokens(raw_words)
        words = filter_repetitions(words)
        
        # Configuration for levels
        if segment_level == "single":
            words = split_thai_words_with_timing(words)
            group_size = 1
            max_d = 2.0
        elif segment_level == "short":
            group_size = 6
            max_d = 3.5
        elif segment_level == "medium":
            group_size = 12
            max_d = 5.0
        else: # long
            group_size = 20
            max_d = 7.0

        current_group = []
        for w in words:
            current_group.append(w)
            
            # Grouping criteria: 
            # 1. Reached count limit 
            # 2. Duration limit reached
            # 3. Gap detected (Pause in speech)
            
            duration = current_group[-1]["end"] - current_group[0]["start"]
            gap = 0
            if len(current_group) > 1:
                # If there's a gap > 0.5s, it's a natural break
                gap = w["start"] - words[words.index(w)-1]["end"]

            if len(current_group) >= group_size or duration >= max_d or gap > 0.5:
                start = current_group[0]["start"]
                end = current_group[-1]["end"]
                text = join_words([item["word"] for item in current_group])
                
                processed_segments.append({
                    "text": text,
                    "start": start,
                    "end": end
                })
                current_group = []
        
        if current_group:
            processed_segments.append({
                "text": join_words([item["word"] for item in current_group]),
                "start": current_group[0]["start"],
                "end": current_group[-1]["end"]
            })

    # Exporting
    if format_type == "txt":
        with open(output_file, "w", encoding="utf-8") as f:
            for seg in processed_segments:
                f.write(seg["text"] + "\n")

    elif format_type == "srt":
        with open(output_file, "w", encoding="utf-8") as f:
            for idx, seg in enumerate(processed_segments, 1):
                f.write(f"{idx}\n")
                f.write(f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n")
                f.write(f"{seg['text']}\n\n")

    return output_file
