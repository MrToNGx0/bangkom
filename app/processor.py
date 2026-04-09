import os

def format_time(t):
    return f"{int(t//3600):02}:{int((t%3600)//60):02}:{int(t%60):02},{int((t%1)*1000):03}"

def process_words(result, words_per_line=1, format_type="txt", file_id="output"):
    os.makedirs("output", exist_ok=True)

    output_file = f"output/{file_id}.{format_type}"

    words = []
    for seg in result["segments"]:
        for w in seg["words"]:
            words.append(w)

    if format_type == "txt":
        with open(output_file, "w", encoding="utf-8") as f:
            buffer = []
            for w in words:
                buffer.append(w["word"])
                if len(buffer) >= words_per_line:
                    f.write(" ".join(buffer) + "\n")
                    buffer = []

    elif format_type == "srt":
        with open(output_file, "w", encoding="utf-8") as f:
            i = 1
            buffer = []
            start = None

            for w in words:
                if start is None:
                    start = w["start"]

                buffer.append(w["word"])

                if len(buffer) >= words_per_line:
                    f.write(f"{i}\n")
                    f.write(f"{format_time(start)} --> {format_time(w['end'])}\n")
                    f.write(" ".join(buffer) + "\n\n")
                    i += 1
                    buffer = []
                    start = None

    return output_file