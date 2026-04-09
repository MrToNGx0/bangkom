import os
import re
from app.core import config

def is_thai(text):
    return bool(re.search('[\u0e00-\u0e7f]', text))

def format_time(t):
    return f"{int(t//3600):02}:{int((t%3600)//60):02}:{int(t%60):02},{int((t%1)*1000):03}"

def join_words(buffer):
    # Join with space only if it's not Thai or looks like English words
    res = ""
    for i, w in enumerate(buffer):
        if i > 0:
            # Add space if previous or current word is not Thai
            if not is_thai(buffer[i-1]) or not is_thai(w):
                res += " "
        res += w
    return res

def process_words(result, words_per_line=1, format_type="txt", file_id="output"):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    output_file = os.path.join(config.OUTPUT_DIR, f"{file_id}.{format_type}")

    words = []
    for seg in result["segments"]:
        for w in seg["words"]:
            words.append(w)

    if not words:
        return ""

    if format_type == "txt":
        with open(output_file, "w", encoding="utf-8") as f:
            buffer = []
            for w in words:
                buffer.append(w["word"].strip())
                if len(buffer) >= words_per_line:
                    f.write(join_words(buffer) + "\n")
                    buffer = []
            # Write remaining buffer
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
                
                # Fill gap for smoother video experience if 1 word per line
                if words_per_line == 1 and i < len(words) - 1:
                    next_start = words[i+1]["start"]
                    if next_start - end < 0.5:
                        end = next_start
                
                text = join_words([w["word"].strip() for w in chunk])
                
                f.write(f"{idx}\n")
                f.write(f"{format_time(start)} --> {format_time(end)}\n")
                f.write(f"{text}\n\n")
                idx += 1

    return output_file
