# 🎧 Bangkom Subtitle Tool (v2.0)

[Thai](#ภาษาไทย) | [English](#english)

---

## ภาษาไทย

เครื่องมือสร้างซับไตเติลอัตโนมัติที่ออกแบบมาเพื่อภาษาไทยโดยเฉพาะ ใช้เทคโนโลยี **Faster-Whisper** สำหรับการถอดความที่รวดเร็วและแม่นยำ เหมาะสำหรับการทำวิดีโอสั้น (Shorts, Reels, TikTok) ที่ต้องการซับไตเติลแบบ "1 คำต่อ 1 ช่วง"

### ✨ คุณสมบัติหลัก
- **Faster-Whisper Engine**: เร็วกว่า Whisper เดิม 2-4 เท่า พร้อมรองรับโมเดล `large-v3-turbo`
- **Smart Thai Spacing**: ระบบจัดการการเว้นวรรคภาษาไทยอัตโนมัติให้อ่านง่ายขึ้น
- **Custom Vocabulary**: ระบบคลังคำเฉพาะทาง แก้ปัญหา AI สะกดชื่อเฉพาะหรือศัพท์เทคนิคผิด
- **Gapless Timing**: ระบบจัดการเวลาซับแบบไม่กระพริบ (Gapless) เหมาะสำหรับซับสไตล์ 1 คำต่อบรรทัด
- **VAD (Voice Activity Detection)**: ลดอาการ AI "เพ้อ" ในช่วงเสียงเงียบ

### 🚀 วิธีการใช้งาน

#### 1. การติดตั้ง (ด้วย Docker - แนะนำ)
```bash
docker-compose up --build
```
เข้าใช้งานผ่านเบราว์เซอร์ที่: `http://localhost:8000`

#### 2. การจัดการคำเฉพาะทาง (Vocab)
- เปิดไฟล์ `app/data/vocab.txt`
- เพิ่มคำศัพท์ที่ต้องการ (บรรทัดละคำ) เช่น ชื่อแบรนด์, ชื่อคน หรือศัพท์เทคนิค
- บันทึกไฟล์และเริ่มประมวลผลใหม่

#### 3. การทำซับวิดีโอ (SRT)
- เลือกไฟล์เสียงหรือวิดีโอ
- ตั้งค่า **Words per line = 1** (สำหรับสไตล์ TikTok/Reels)
- เลือก Format เป็น **SRT**
- นำไฟล์ที่ได้ไปใส่ในโปรแกรมตัดต่อ (Premiere Pro, CapCut, etc.)

---

## English

An automated subtitle generation tool specially optimized for Thai and English. Powered by **Faster-Whisper** for high-speed, high-accuracy transcription. Ideal for short-form content (Shorts, Reels, TikTok) requiring "1 word per segment" subtitles.

### ✨ Key Features
- **Faster-Whisper Engine**: 2-4x faster than original Whisper, supporting `large-v3-turbo`.
- **Smart Thai Spacing**: Automatically manages Thai word spacing for better readability.
- **Custom Vocabulary**: A simple system to ensure AI correctly spells technical terms or brand names.
- **Gapless Timing**: Smooth subtitle transitions, perfect for the 1-word-per-line style.
- **VAD (Voice Activity Detection)**: Filters out silence to prevent AI hallucinations.

### 🚀 How to Use

#### 1. Installation (via Docker - Recommended)
```bash
docker-compose up --build
```
Access the UI at: `http://localhost:8000`

#### 2. Managing Custom Vocabulary
- Open `app/data/vocab.txt`
- Add your specific terms (one per line), such as brand names, people's names, or technical jargon.
- Save the file and re-process your media.

#### 3. Generating Video Subtitles (SRT)
- Upload your audio or video file.
- Set **Words per line = 1** (for TikTok/Reels style).
- Select **SRT** format.
- Import the generated SRT into your editor (Premiere Pro, CapCut, etc.).

---

### 📂 Project Structure
- `app/api/`: API Routes (FastAPI)
- `app/services/`: Core Logic (Whisper, Processor)
- `app/core/`: Configuration
- `app/data/`: Vocabulary files
- `web/`: Frontend Interface (Tailwind CSS)

### 🛠 Tech Stack
- FastAPI (Python)
- Faster-Whisper (CTranslate2)
- Docker
- Tailwind CSS
