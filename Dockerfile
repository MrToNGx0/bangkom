FROM pytorch/pytorch:latest

WORKDIR /app

RUN mkdir -p /app/static /app/input /app/output

COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel

RUN pip install openai-whisper --no-build-isolation

RUN pip install fastapi==0.110.0 uvicorn[standard]==0.27.0 python-multipart==0.0.9 ffmpeg-python

RUN python -c "import whisper; whisper.load_model('base')"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]