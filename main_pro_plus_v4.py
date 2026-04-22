import os
import sys
import csv
from dict_manager_ui import open_dict_manager_window
from post_manager import PostManagerTab
import json
import random
import threading
import subprocess
import urllib.request
import urllib.error
from queue import Queue, Empty

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from dictionary_lib import get_dict, lookup_word, search_words


# =========================================================
# CONFIG
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")
DEFAULT_CSV_FILE = os.path.join(BASE_DIR, "data.csv")
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg.exe")
FONT_PATH = "C\\:/Windows/Fonts/arial.ttf"

VIDEO_W = 720
VIDEO_H = 1280
APP_TITLE = "ENGLISH VOCAB FACTORY V2"

GRADIENT_THEMES = [
    ("#0f0c29", "#302b63"),
    ("#1a1a2e", "#16213e"),
    ("#0d0d0d", "#1a1a2e"),
    ("#200122", "#6f0000"),
    ("#0f2027", "#203a43"),
    ("#1f1c2c", "#928dab"),
]

# ===== LOGO CONFIG =====
LOGO_ENABLED = True
LOGO_PATH    = os.path.join(BASE_DIR, "logo.jpg")
LOGO_SIZE    = 80       # kích thước px
LOGO_POS     = "top-left"
LOGO_ALPHA   = 0.85     # độ trong suốt (chỉ có tác dụng với PNG)

# =========================================================
# AI CONFIG
# =========================================================
AI_PROVIDER = "gemini"
GEMINI_API_KEY = "AIzaSyCzVQJOuQBq3PrVq6QmZSYW0p3vEBZyRz4"
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ================= VOICE CONFIG =================
ELEVENLABS_API_KEY = "sk_a1bc2ad9e885cd47f12bc8771af393e5719694106d241dfa"
ELEVENLABS_VOICE_ID = "TYKLc7ViOIGE13dSZYlK"  # Rachel

# ================= VOICE MODE =================
VOICE_MODE = "edge"  
# "edge" | "eleven" | "hybrid"

EDGE_VOICE_EN = "en-US-AriaNeural"
EDGE_VOICE_VI = "vi-VN-HoaiMyNeural"

# ================= BACKGROUND VIDEO CONFIG =================
BG_SOURCE = "pexels"  # "pexels" | "pixabay" | "giphy" | "mixkit" | "none"
VIDEO_THEME = "none"  # "none" | "funny" | "kids" | "serious" | "nature" | "cartoon" | "anime" | "sport"

# Cấu hình chi tiết từng theme: prefix (đầu query) và suffix (cuối query)
_THEME_CONFIG = {
    "none":    {"prefix": "",                 "suffix": "",              "fallback": []},
    "funny":   {"prefix": "funny",            "suffix": "",              "fallback": ["funny cute", "comedy"]},
    "kids":    {"prefix": "cartoon kids",     "suffix": "",              "fallback": ["kids colorful", "children"]},
    "serious": {"prefix": "",                 "suffix": "cinematic",     "fallback": ["professional", "dramatic"]},
    "nature":  {"prefix": "nature",           "suffix": "outdoor",       "fallback": ["landscape", "outdoor"]},
    "cartoon": {"prefix": "animated cartoon", "suffix": "",              "fallback": ["cartoon", "animation"]},
    "anime":   {"prefix": "anime",            "suffix": "animated",      "fallback": ["anime", "japanese animation"]},
    "sport":   {"prefix": "sport action",     "suffix": "",              "fallback": ["active", "sport"]},
}

# Stop-words khi trích keyword từ câu ví dụ
_EXAMPLE_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "i", "you", "he", "she", "it", "we", "they", "my", "your", "his", "her",
    "this", "that", "these", "those", "to", "of", "in", "on", "at", "for",
    "with", "by", "from", "up", "out", "as", "into", "and", "or", "but",
    "so", "very", "can", "do", "does", "did", "have", "has", "had",
    "not", "no", "its", "our", "their", "every", "all", "also",
}

PEXELS_API_KEY    = "eGrAHB19dv61ecn12RJJRLncjWraIPV7JEKWddx8eUpAkP41kJ9aXNUJ"
PIXABAY_API_KEY   = "55500745-51b288484ac4fec66370bf668"
GIPHY_API_KEY     = "UDw6zTOcvK4sn9GrQpOGf27hd8LKTNvA"

BG_VIDEO_DIR = os.path.join(BASE_DIR, "bg_cache")  # cache video tải về

# =========================================================
# AI LOOKUP
# =========================================================
_GEMINI_PROMPT = (
    'Dịch từ tiếng Anh sang tiếng Việt. Quy tắc bắt buộc:\n'
    '- meaning: CHỈ 1-3 từ tiếng Việt, KHÔNG giải thích, KHÔNG dấu câu thừa\n'
    '- example: 1 câu tiếng Anh ngắn (tối đa 8 từ), tự nhiên, KHÔNG bắt đầu bằng "This is"\n'
    '  Gợi ý mẫu câu đa dạng: "She loves...", "He can...", "I always...", "They are...", "We need..."\n'
    'Ví dụ đúng: duck → {{"meaning":"con vịt","example":"The duck swims in the pond."}}\n'
    'Ví dụ đúng: happy → {{"meaning":"vui vẻ","example":"She feels happy today."}}\n'
    'Ví dụ đúng: run → {{"meaning":"chạy","example":"He runs every morning."}}\n'
    'Ví dụ SAI: duck → {{"meaning":"một loài chim sống dưới nước","example":"This is a duck."}}\n'
    'Từ cần dịch: "{word}"\n'
    'Chỉ trả về JSON, không thêm gì khác.'
)

def _call_gemini(word, api_key):
    prompt = _GEMINI_PROMPT.format(word=word)
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")
    url = f"{GEMINI_ENDPOINT}?key={api_key}"
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = text.replace("```json", "").replace("```", "").strip()
    result = json.loads(text)
    meaning = result["meaning"].strip()
    example = result["example"].strip()
    # Bảo vệ: nếu AI vẫn trả về nghĩa dài → lấy phần trước dấu phẩy/chấm đầu tiên
    if len(meaning) > 20:
        meaning = meaning.split(",")[0].split(".")[0].strip()
    return meaning, example


import random as _random

_FALLBACK_EXAMPLE_TEMPLATES = [
    "She loves the {w}.",
    "He uses a {w} every day.",
    "I can see a {w} here.",
    "They found a {w} outside.",
    "We need a {w} now.",
    "The {w} is very useful.",
    "Look at that {w}!",
    "She has a beautiful {w}.",
]

def _make_fallback_example(word: str) -> str:
    """Tạo câu ví dụ đa dạng khi không có AI."""
    w = word.lower()
    return _random.choice(_FALLBACK_EXAMPLE_TEMPLATES).format(w=w)


def ai_lookup_word(word, provider=None, gemini_key=None):
    p = provider or AI_PROVIDER
    gk = gemini_key or GEMINI_API_KEY

    # 1. Offline dict trước (nhanh nhất)
    result = lookup_word(word)
    if result:
        meaning, example, group = result
        return meaning, example, "offline"

    # 2. Gemini AI (nếu có API key)
    if p == "gemini" and gk:
        try:
            meaning, example = _call_gemini(word, gk)
            if meaning and example:
                save_to_offline(word, meaning, example)
                return meaning, example, "gemini"
        except Exception as e:
            print(f"[AI] Gemini fail: {word} → {e}")

    # 3. Google Translate — dịch từ gốc trực tiếp → nghĩa ngắn gọn
    vi = translate_google(word)
    if vi:
        example = _make_fallback_example(word)
        save_to_offline(word, vi, example)
        return vi, example, "google"

    # 4. Fallback
    return f"({word})", _make_fallback_example(word), "fallback"


def translate_google(word):
    """Dịch Anh → Việt"""
    try:
        import requests
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=vi&dt=t&q={word}"
        r = requests.get(url, timeout=10)

        data = r.json()
        return data[0][0][0]

    except Exception as e:
        print(f"[ONLINE] google translate fail: {e}")
        return None
    
# ✅ MỚI - lưu vào dictionary_lib (persistent)
def save_to_offline(word, meaning, example, group="AUTO"):
    d = get_dict()
    if group not in d.get_groups():
        d.add_group(group)
    d.add_word(group, word, meaning, example)
    d.save()


# =========================================================
# HELPERS
# =========================================================
def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def check_ffmpeg():
    if not os.path.exists(FFMPEG_PATH):
        return False, f"Không tìm thấy ffmpeg.exe tại:\n{FFMPEG_PATH}"
    return True, "FFmpeg sẵn sàng ✅"


def normalize(value):
    return str(value).strip() if value is not None else ""


def safe_ps_text(text):
    text = str(text)
    text = text.replace("`", "``")
    text = text.replace('"', '`"')
    text = text.replace("$", "`$")
    return text


def safe_ffmpeg_text(text):
    text = str(text)
    replacements = [
        ("\\", "\\\\"),
        (":", "\\:"),
        ("'", "\\'"),
        ("%", "\\%"),
        ("[", "\\$"),
        ("]", "\\$"),
        (",", "\\,"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def auto_split_words(word_list, group_size=6):
    groups = []
    for i in range(0, len(word_list), group_size):
        chunk = word_list[i:i + group_size]
        if len(chunk) > 0:
            while len(chunk) < group_size:
                chunk.append(chunk[-1])
            groups.append(chunk)
    return groups


def build_row_from_words(word_group):
    row = []
    for word in word_group:
        meaning, example, source = ai_lookup_word(
            word,
            provider=AI_PROVIDER,
            gemini_key=GEMINI_API_KEY
        )
        row.extend([word, meaning, example])
    return row


def validate_row(row):
    if len(row) != 18:
        return False, f"Cần đúng 18 cột, hiện có {len(row)}"
    for i, v in enumerate(row):
        if normalize(v) == "":
            return False, f"Cột {i + 1} đang rỗng"
    return True, "OK"


def validate_csv(file_path):
    try:
        rows = []
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                ok, msg = validate_row(row)
                if not ok:
                    return False, f"Dòng {idx + 1}: {msg}", None
                rows.append(row)
        if not rows:
            return False, "File CSV rỗng", None
        return True, f"Hợp lệ, có {len(rows)} dòng", rows
    except Exception as e:
        return False, f"Lỗi đọc file: {e}", None


# =========================================================
# TTS - TÁCH GIỌNG ANH / VIỆT
# =========================================================

def get_available_voices():
    """
    Lấy danh sách voice có sẵn trên Windows
    Trả về dict: {name_lower: full_name}
    """
    ps = '''
Add-Type -AssemblyName System.Speech;
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;
$s.GetInstalledVoices() | ForEach-Object {
    $_.VoiceInfo.Name
};
$s.Dispose();
'''
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=15
        )
        voices = {}
        for line in r.stdout.strip().splitlines():
            name = line.strip()
            if name:
                voices[name.lower()] = name
        return voices
    except Exception:
        return {}


def find_best_voice(voices: dict, lang: str) -> str:
    """
    Tìm voice phù hợp nhất theo ngôn ngữ.
    lang: "en" hoặc "vi"
    Trả về tên voice hoặc "" (dùng mặc định)
    """
    if lang == "en":
        # Ưu tiên: David, Zira, Mark, bất kỳ voice có "en"
        priority = ["david", "zira", "mark", "hazel", "george", "en-us", "en-gb"]
    else:
        # Ưu tiên: voice tiếng Việt
        priority = ["linh", "an", "viet", "vi-vn", "vietnam"]

    for keyword in priority:
        for name_lower, full_name in voices.items():
            if keyword in name_lower:
                return full_name

    # Fallback: trả về voice đầu tiên có sẵn
    if voices:
        return list(voices.values())[0]
    return ""


def make_voice_with_lang(text: str, filename: str, voice_name: str = ""):
    """
    Tạo file WAV với voice chỉ định.
    voice_name: tên đầy đủ của voice (hoặc "" để dùng mặc định)
    """
    safe = safe_ps_text(text)

    if voice_name:
        safe_voice = voice_name.replace('"', '`"')
        select_voice_cmd = f'$s.SelectVoice("{safe_voice}");'
    else:
        select_voice_cmd = ""

    ps = f'''
Add-Type -AssemblyName System.Speech;
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;
$s.Rate = -1;
$s.Volume = 100;
{select_voice_cmd}
$s.SetOutputToWaveFile("{filename}");
$s.Speak("{safe}");
$s.Dispose();
'''
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=60
    )
    if r.returncode != 0 or not os.path.exists(filename):
        raise RuntimeError(r.stderr.strip() or f"TTS thất bại cho: {text[:30]}")


def concat_wav_files(wav_list: list, output_wav: str):
    """
    Ghép nhiều file WAV thành 1 bằng FFmpeg
    """
    list_file = output_wav + "_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for w in wav_list:
            p = os.path.abspath(w).replace("\\", "/")
            f.write(f"file '{p}'\n")

    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_wav
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if os.path.exists(list_file):
        os.remove(list_file)


# =========================================================
# TTS - ELEVENLABS + EDGE TTS
# =========================================================
import requests
import asyncio
import edge_tts

def tts_elevenlabs(text, output_file):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2"
    }
    r = requests.post(url, json=data, headers=headers, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:200]}")
    with open(output_file, "wb") as f:
        f.write(r.content)


async def _edge_tts_async(text, output_file, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def tts_edge(text, output_file, voice=None):
    v = voice or EDGE_VOICE_VI
    asyncio.run(_edge_tts_async(text, output_file, v))

def is_audio_valid(path):
    return os.path.exists(path) and os.path.getsize(path) > 1000

import time as _time

def _tts_edge_with_retry(text, output_file, voice, retries=3):
    """Gọi edge_tts với retry tự động, xử lý lỗi mạng/rate limit."""
    clean_text = text.replace("...", "").strip() or text
    attempts = [text, clean_text, clean_text]  # lần 1: có pause, lần 2-3: không pause
    last_err = None
    for i, t in enumerate(attempts[:retries]):
        try:
            asyncio.run(_edge_tts_async(t, output_file, voice))
            if is_audio_valid(output_file):
                return
        except Exception as e:
            last_err = e
            print(f"[TTS] edge retry {i+1}/{retries}: '{t[:30]}' → {e}")
            _time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"edge_tts thất bại sau {retries} lần: {last_err}")


def make_tts_smart(word, meaning, example, prefix):
    wav_word = prefix + "_word.mp3"
    wav_mean = prefix + "_mean.mp3"
    wav_ex   = prefix + "_ex.mp3"

    PAUSE = "..."

    if VOICE_MODE == "edge":
        _tts_edge_with_retry(word + PAUSE, wav_word, EDGE_VOICE_EN)
        _tts_edge_with_retry(meaning + PAUSE, wav_mean, EDGE_VOICE_VI)
        _tts_edge_with_retry(example + PAUSE, wav_ex, EDGE_VOICE_EN)

    elif VOICE_MODE == "eleven":
        try:
            tts_elevenlabs(word + PAUSE, wav_word)
            if not is_audio_valid(wav_word):
                raise Exception("empty")
        except Exception as e:
            print(f"[TTS] Eleven fail word: {e}")
            tts_elevenlabs(word, wav_word)

        try:
            tts_elevenlabs(meaning + PAUSE, wav_mean)
            if not is_audio_valid(wav_mean):
                raise Exception("empty")
        except Exception as e:
            print(f"[TTS] Eleven fail meaning: {e}")
            tts_elevenlabs(meaning, wav_mean)

        try:
            tts_elevenlabs(example + PAUSE, wav_ex)
            if not is_audio_valid(wav_ex):
                raise Exception("empty")
        except Exception as e:
            print(f"[TTS] Eleven fail example: {e}")
            tts_elevenlabs(example, wav_ex)

    else:  # hybrid
        try:
            tts_elevenlabs(word + PAUSE, wav_word)
            if not is_audio_valid(wav_word):
                raise Exception("empty")
        except:
            _tts_edge_with_retry(word + PAUSE, wav_word, EDGE_VOICE_EN)

        try:
            tts_elevenlabs(example + PAUSE, wav_ex)
            if not is_audio_valid(wav_ex):
                raise Exception("empty")
        except:
            _tts_edge_with_retry(example + PAUSE, wav_ex, EDGE_VOICE_EN)

        try:
            _tts_edge_with_retry(meaning + PAUSE, wav_mean, EDGE_VOICE_VI)
        except:
            tts_elevenlabs(meaning + PAUSE, wav_mean)

    return [wav_word, wav_mean, wav_ex]


def concat_audio_mp3(files, output):
    """Ghép nhiều file mp3 thành 1 - dùng mp3 codec đúng chuẩn"""
    list_file = output + "_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for file in files:
            p = os.path.abspath(file).replace("\\", "/")
            f.write(f"file '{p}'\n")

    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c:a", "libmp3lame",   # ← đúng codec cho .mp3
        "-ar", "44100",
        "-b:a", "128k",
        "-f", "mp3",            # ← ép đúng format
        output
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if os.path.exists(list_file):
        os.remove(list_file)

    # ✅ Kiểm tra output có hợp lệ không
    if not os.path.exists(output) or os.path.getsize(output) < 1000:
        raise RuntimeError(f"concat_audio_mp3 thất bại: {output}")




# =========================================================
# BACKGROUND VIDEO FETCHER
# =========================================================
import urllib.request
import urllib.parse

def ensure_bg_dir():
    os.makedirs(BG_VIDEO_DIR, exist_ok=True)


def fetch_pexels_video(keyword):
    try:
        q = urllib.parse.quote(keyword)
        url = f"https://api.pexels.com/videos/search?query={q}&per_page=5&orientation=portrait"
        
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": PEXELS_API_KEY,
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.pexels.com/",
                "Origin": "https://www.pexels.com",
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[Pexels] HTTP {resp.status} OK")
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            print(f"[Pexels] HTTP {e.code}: {body[:200]}")
            return None

        videos = data.get("videos", [])
        if not videos:
            print("[Pexels] Không có video nào!")
            return None

        for v in videos:
            files = sorted(v["video_files"], key=lambda x: x.get("width", 0))
            for f in files:
                link = f.get("link", "")
                w = f.get("width", 0)
                if link.endswith(".mp4") and 480 <= w <= 1280:
                    print(f"[Pexels] ✅ Chọn: width={w}")
                    return link
            for f in files:
                link = f.get("link", "")
                if link.endswith(".mp4"):
                    return link

    except Exception as e:
        print(f"[Pexels] Lỗi: {e}")
        return None




def fetch_pixabay_video(keyword):
    """Tải video từ Pixabay"""
    try:
        q = urllib.parse.quote(keyword)
        url = (f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}"
               f"&q={q}&per_page=5&video_type=film")
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        hits = data.get("hits", [])
        if not hits:
            return None
        return hits[0]["videos"]["small"]["url"]
    except Exception:
        return None


def fetch_giphy_gif(keyword):
    try:
        import requests as req_lib
        q = urllib.parse.quote(keyword)
        url = (f"https://api.giphy.com/v1/gifs/search"
               f"?api_key={GIPHY_API_KEY}&q={q}&limit=10&rating=g")

        resp = req_lib.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"[Giphy] HTTP {resp.status_code}")
            return None

        data = resp.json()
        results = data.get("data", [])
        if not results:
            return None

        for item in results:
            images = item.get("images", {})

            # ✅ Ưu tiên MP4 (FFmpeg xử lý tốt hơn GIF nhiều)
            mp4_url = images.get("original_mp4", {}).get("mp4", "")
            if mp4_url:
                print(f"[Giphy] ✅ MP4: {mp4_url[:60]}...")
                return mp4_url

        # Fallback: GIF nhỏ
        gif_url = results[0]["images"].get("fixed_height_small", {}).get("url", "")
        return gif_url or None

    except Exception as e:
        print(f"[GIPHY] Lỗi: {e}")
        return None



def fetch_mixkit_video(keyword):
    """
    Mixkit không có API chính thức → dùng Pexels làm fallback
    (hoặc bạn có thể hardcode 1 số video mixkit đẹp)
    """
    return fetch_pexels_video(keyword)


def download_bg_file(url, dest_path):
    """Download file về local với browser headers đầy đủ"""
    try:
        import requests as req_lib
        
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.pexels.com/",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        resp = req_lib.get(url, headers=headers, timeout=60, stream=True)
        print(f"[download] HTTP {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"[download] Lỗi HTTP: {resp.status_code}")
            return False
        
        total = 0
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)
        
        print(f"[download] Đã tải: {total:,} bytes")
        
        if total < 1000:
            print(f"[download] File quá nhỏ, bỏ qua")
            os.remove(dest_path)
            return False
        
        return True
        
    except Exception as e:
        print(f"[download] Lỗi: {e}")
        return False



def _extract_visual_words(example: str, word: str) -> list:
    """
    Trích các từ hình ảnh (visual nouns/verbs) từ câu ví dụ.
    Bỏ stop-words, giữ tối đa 3 từ có nghĩa nhất.
    """
    import re
    tokens = re.findall(r"[a-zA-Z]+", example.lower())
    word_lower = word.lower()
    seen = set()
    result = []
    for t in tokens:
        if t in _EXAMPLE_STOP_WORDS:
            continue
        # Loại chính từ đang học (đã có sẵn trong query chính)
        if t == word_lower or t == word_lower + "s" or t == word_lower + "ing":
            continue
        if t not in seen:
            seen.add(t)
            result.append(t)
        if len(result) >= 3:
            break
    return result


def build_smart_keywords(word: str, example: str = "",
                         theme: str = None, topic: str = "") -> list:
    """
    Xây dựng fallback-chain keyword để tìm video nền.
    Kết hợp: từ vựng + chủ đề bài viết (topic) + từ visual trong câu ví dụ + style theme.
    Trả về list[str] theo thứ tự ưu tiên — thử từng cái cho đến khi có kết quả.

    Ví dụ:
      word="swim", example="The duck swims in the pond.", theme="kids", topic="Animals"
      → ["cartoon kids duck swim pond animals",
         "cartoon kids duck swim pond",
         "cartoon kids swim duck",
         "cartoon kids swim",
         "cartoon kids animals",
         "kids colorful", "children"]
    """
    t = theme or VIDEO_THEME
    cfg = _THEME_CONFIG.get(t, _THEME_CONFIG["none"])
    prefix  = cfg["prefix"]
    suffix  = cfg["suffix"]
    fallbacks = cfg["fallback"]

    visual = _extract_visual_words(example, word)

    # Chuẩn hoá topic thành 1-2 từ keyword hữu ích
    topic_kw = ""
    if topic:
        import re as _re
        topic_tokens = _re.findall(r"[a-zA-Z]+", topic.lower())
        topic_kw = " ".join(
            tok for tok in topic_tokens
            if tok not in _EXAMPLE_STOP_WORDS and len(tok) > 2
        )[:30]

    def _q(*parts):
        tokens = []
        if prefix:
            tokens.append(prefix)
        tokens.extend([p for p in parts if p])
        if suffix:
            tokens.append(suffix)
        return " ".join(tokens).strip()

    chain = []

    # Level 1: word + tất cả visual + topic (context đầy đủ nhất)
    if visual and topic_kw:
        chain.append(_q(word, visual[0], topic_kw))

    # Level 2: word + visual + không topic
    if visual:
        chain.append(_q(word, *visual[:2]))

    # Level 3: word + visual[0]
    if visual:
        chain.append(_q(word, visual[0]))

    # Level 4: word + topic (bỏ visual)
    if topic_kw:
        chain.append(_q(word, topic_kw))

    # Level 5: chỉ word + theme style
    chain.append(_q(word))

    # Level 6: topic + theme style (fallback không có word)
    if topic_kw:
        chain.append(_q(topic_kw))

    # Level 7: visual + theme style
    if visual:
        chain.append(_q(visual[0]))

    # Level 8: keyword thuần chủ đề UI
    chain.extend(fallbacks)

    # Loại trùng, giữ thứ tự
    seen = set()
    result = []
    for kw in chain:
        if kw and kw not in seen:
            seen.add(kw)
            result.append(kw)

    return result if result else [word]


def get_bg_video(word: str, example: str = "", source: str = None,
                 theme: str = None, topic: str = ""):
    """
    Tìm và cache video nền phù hợp với từ + câu ví dụ + chủ đề bài viết + theme UI.
    Thử lần lượt các keyword trong fallback chain cho đến khi có kết quả.

    Args:
        word:    Từ vựng đang học ("swim")
        example: Câu ví dụ ("The duck swims in the pond.")
        source:  Nguồn video ("pexels" / "pixabay" / "giphy" / "mixkit")
        theme:   Theme UI ("kids" / "funny" / ...)
        topic:   Chủ đề bài viết ("Animals" / "Food" / ...) — từ PostManager
    """
    ensure_bg_dir()
    src = source or BG_SOURCE
    t   = theme or VIDEO_THEME

    # Cache key: word + theme + topic (stable, không phụ thuộc visual)
    theme_tag = t if t != "none" else "raw"
    topic_tag = topic.lower().replace(" ", "_")[:10] if topic else ""
    safe_word = word.lower().replace(" ", "_")[:15]
    cache_name = f"{src}_{theme_tag}_{safe_word}"
    if topic_tag:
        cache_name += f"_{topic_tag}"
    cache_path = os.path.join(BG_VIDEO_DIR, cache_name + ".mp4")

    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 1000:
        print(f"[BG] Cache hit: {os.path.basename(cache_path)}")
        return cache_path

    keywords = build_smart_keywords(word, example, t, topic)
    print(f"[BG] word='{word}' topic='{topic}' theme='{t}'")
    print(f"[BG] Keyword chain: {keywords}")

    for kw in keywords:
        print(f"[BG] Thử: '{kw}'")
        url = None
        if src == "pexels":
            url = fetch_pexels_video(kw)
        elif src == "pixabay":
            url = fetch_pixabay_video(kw)
        elif src == "giphy":
            url = fetch_giphy_gif(kw)
        elif src == "mixkit":
            url = fetch_mixkit_video(kw)

        if url:
            print(f"[BG] ✅ Tìm thấy với '{kw}'")
            ok = download_bg_file(url, cache_path)
            return cache_path if ok else None

    print(f"[BG] ❌ Không tìm thấy video nào cho '{word}' / '{topic}'")
    return None

def get_logo_overlay_filter(logo_path, size, pos, alpha):
        """Tạo FFmpeg filter string để overlay logo PNG"""
        if not logo_path or not os.path.exists(logo_path):
            return None, None

        # Escape path cho FFmpeg
        safe_path = logo_path.replace("\\", "/").replace(":", "\\:")

        # Tọa độ theo vị trí
        margin = 20
        pos_map = {
            "top-left":     f"x={margin}:y={margin}",
            "top-right":    f"x=W-w-{margin}:y={margin}",
            "bottom-left":  f"x={margin}:y=H-h-{margin}",
            "bottom-right": f"x=W-w-{margin}:y=H-h-{margin}",
        }
        xy = pos_map.get(pos, f"x={margin}:y={margin}")

        # Filter: scale logo + set alpha + overlay
        logo_filter = f"[1:v]scale={size}:-1,format=rgba,colorchannelmixer=aa={alpha}[logo]"
        overlay_filter = f"[0:v][logo]overlay={xy}"

        return logo_filter, overlay_filter
# =========================================================
# VIDEO ENGINE
# =========================================================
class VideoEngine:
    def __init__(self, log_fn, progress_fn, done_fn):
        self.log_fn = log_fn
        self.progress_fn = progress_fn
        self.done_fn = done_fn
        self.queue = Queue()
        self.stop_event = threading.Event()
        self.total = 0
        self.done_count = 0
        self.running = False
        self.current_topic = ""  # Chủ đề bài viết — truyền từ PostManager khi render

    def log(self, msg):
        if self.log_fn:
            self.log_fn(msg)

    def make_voice(self, text, out_wav):
        safe = safe_ps_text(text)
        ps = f'''
Add-Type -AssemblyName System.Speech;
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;
$s.Rate = -1;
$s.Volume = 100;
$s.SetOutputToWaveFile("{out_wav}");
$s.Speak("{safe}");
$s.Dispose();
'''
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=60
        )
        if r.returncode != 0 or not os.path.exists(out_wav):
            raise RuntimeError(r.stderr.strip() or "TTS thất bại")

    def get_duration(self, wav_file):
        probe = os.path.join(BASE_DIR, "ffprobe.exe")
        if not os.path.exists(probe):
            return 4.0
        try:
            r = subprocess.run(
                [probe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", wav_file],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=20
            )
            d = float(r.stdout.strip())
            return max(d + 0.5, 3.0)
        except Exception:
            return 4.0
        
    # def render_segment(self, word, meaning, example, vid_idx, seg_idx):
    #     ensure_output_dir()

    #     prefix    = os.path.join(OUTPUT_DIR, f"_tts_{vid_idx}_{seg_idx}")
    #     seg_mp4   = os.path.join(OUTPUT_DIR, f"_s{vid_idx}_{seg_idx}.mp4")
    #     final_audio = prefix + "_final.mp3"

    #     # --- TTS ---
    #     audio_parts = make_tts_smart(word, meaning, example, prefix)
    #     concat_audio_mp3(audio_parts, final_audio)
    #     dur = self.get_duration(final_audio)

    #     # --- Text overlay ---
    #     w_text       = safe_ffmpeg_text(word.upper())
    #     m_text       = safe_ffmpeg_text(f"({meaning})")
    #     e_text       = safe_ffmpeg_text(example)
    #     counter_text = safe_ffmpeg_text(f"{seg_idx}/6")

    #     vf_text = ",".join([
    #         f"drawtext=fontfile='{FONT_PATH}':text='{counter_text}'"
    #         f":fontcolor=white@0.5:fontsize=32:x=w-text_w-30:y=30",

    #         f"drawtext=fontfile='{FONT_PATH}':text='{w_text}'"
    #         f":fontcolor=#FFD700:fontsize=80"
    #         f":x=(w-text_w)/2:y=(h/2)-140"
    #         f":shadowcolor=black:shadowx=3:shadowy=3",

    #         f"drawtext=fontfile='{FONT_PATH}':text='{m_text}'"
    #         f":fontcolor=white:fontsize=50"
    #         f":x=(w-text_w)/2:y=(h/2)-20"
    #         f":shadowcolor=black:shadowx=2:shadowy=2",

    #         f"drawtext=fontfile='{FONT_PATH}':text='{e_text}'"
    #         f":fontcolor=#cccccc:fontsize=34"
    #         f":x=(w-text_w)/2:y=(h/2)+80"
    #         f":shadowcolor=black:shadowx=1:shadowy=1",
    #     ])

    #     # --- Lấy video background ---
    #     bg_file = None
    #     if BG_SOURCE != "none":
    #         try:
    #             bg_file = get_bg_video(word, BG_SOURCE)
    #         except Exception:
    #             bg_file = None

    #             # --- Build FFmpeg command ---
    #             if bg_file and os.path.exists(bg_file):
    #                 is_gif = bg_file.endswith(".gif")
    #                 fps = "15" if is_gif else "25"
    #                 loop_flag = ["-ignore_loop", "0"] if is_gif else []

    #                 vf = (
    #                     f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=increase,"
    #                     f"crop={VIDEO_W}:{VIDEO_H},"
    #                     f"format=yuv420p,"
    #                     + vf_text
    #                 )

    #                 if LOGO_ENABLED and LOGO_PATH and os.path.exists(LOGO_PATH):
    #                     # ✅ FIX: tính tọa độ đúng
    #                     margin = 20
    #                     pos_map = {
    #                         "top-left":     f"{margin}:{margin}",
    #                         "top-right":    f"W-w-{margin}:{margin}",
    #                         "bottom-left":  f"{margin}:H-h-{margin}",
    #                         "bottom-right": f"W-w-{margin}:H-h-{margin}",
    #                     }
    #                     xy = pos_map.get(LOGO_POS, f"{margin}:{margin}")

    #                     safe_logo = LOGO_PATH.replace("\\", "/").replace(":", "\\:")

    #                     # ✅ FIX: complex_filter đúng cú pháp
    #                     complex_filter = (
    #                         f"[0:v]scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=increase,"
    #                         f"crop={VIDEO_W}:{VIDEO_H},format=yuv420p,"
    #                         f"{vf_text}[bg];"
    #                         f"[2:v]scale={LOGO_SIZE}:-1,format=rgba,"
    #                         f"colorchannelmixer=aa={LOGO_ALPHA}[logo];"
    #                         f"[bg][logo]overlay={xy}[out]"
    #                     )

    #                     cmd = (
    #                         [FFMPEG_PATH, "-y"]
    #                         + loop_flag
    #                         + ["-stream_loop", "-1", "-i", bg_file]
    #                         + ["-i", final_audio]
    #                         + ["-i", LOGO_PATH]
    #                         + ["-filter_complex", complex_filter]
    #                         + ["-map", "[out]", "-map", "1:a"]
    #                         + ["-t", str(dur), "-r", fps]
    #                         + ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"]
    #                         + ["-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100"]
    #                         + ["-shortest", seg_mp4]
    #                     )
    #                 else:
    #                     # Không có logo
    #                     cmd = (
    #                         [FFMPEG_PATH, "-y"]
    #                         + loop_flag
    #                         + ["-stream_loop", "-1", "-i", bg_file]
    #                         + ["-i", final_audio]
    #                         + ["-vf", vf, "-t", str(dur), "-r", fps]
    #                         + ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"]
    #                         + ["-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100"]
    #                         + ["-shortest", seg_mp4]
    #                     )
    #             else:
    #                 # Fallback: gradient màu
    #                 theme = random.choice(GRADIENT_THEMES)
    #                 bg_color = theme[0]
    #                 cmd = [
    #                     FFMPEG_PATH, "-y",
    #                     "-f", "lavfi",
    #                     "-i", f"color=c={bg_color}:s={VIDEO_W}x{VIDEO_H}:d={dur}",
    #                     "-i", final_audio,
    #                     "-vf", vf_text,
    #                     "-shortest",
    #                     "-c:v", "libx264",
    #                     "-pix_fmt", "yuv420p",
    #                     "-c:a", "aac",
    #                     seg_mp4
    #                 ]

    #     r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    #     # Cleanup
    #     for f in audio_parts + [final_audio]:
    #         try:
    #             if os.path.exists(f):
    #                 os.remove(f)
    #         except Exception:
    #             pass

    #     if r.returncode != 0:
    #         raise RuntimeError(r.stderr[-500:] or "Lỗi render segment")

    #     return None, seg_mp4
    
    def render_segment(self, word, meaning, example, vid_idx, seg_idx, topic: str = ""):
        ensure_output_dir()

        prefix      = os.path.join(OUTPUT_DIR, f"_tts_{vid_idx}_{seg_idx}")
        seg_mp4     = os.path.join(OUTPUT_DIR, f"_s{vid_idx}_{seg_idx}.mp4")
        final_audio = prefix + "_final.mp3"

        # ===================== TTS =====================
        audio_parts = make_tts_smart(word, meaning, example, prefix)
        concat_audio_mp3(audio_parts, final_audio)
        dur = self.get_duration(final_audio)

        # ===================== TEXT OVERLAY (TikTok style) =====================
        w_text       = safe_ffmpeg_text(word.upper())
        m_text       = safe_ffmpeg_text(f"({meaning})")
        e_text       = safe_ffmpeg_text(example)
        counter_text = safe_ffmpeg_text(f"{seg_idx}/6")

        vf_text = ",".join([
            # Counter nhỏ góc phải
            f"drawtext=fontfile='{FONT_PATH}':text='{counter_text}'"
            f":fontcolor=white@0.5:fontsize=32:x=w-text_w-30:y=30",

            # WORD - to, vàng, nổi bật
            f"drawtext=fontfile='{FONT_PATH}':text='{w_text}'"
            f":fontcolor=#FFD700:fontsize=90"
            f":x=(w-text_w)/2:y=(h/2)-200"
            f":shadowcolor=black:shadowx=4:shadowy=4",

            # MEANING - trắng
            f"drawtext=fontfile='{FONT_PATH}':text='{m_text}'"
            f":fontcolor=white:fontsize=55"
            f":x=(w-text_w)/2:y=(h/2)-50"
            f":shadowcolor=black:shadowx=2:shadowy=2",

            # EXAMPLE - xám nhạt
            f"drawtext=fontfile='{FONT_PATH}':text='{e_text}'"
            f":fontcolor=#cccccc:fontsize=38"
            f":x=(w-text_w)/2:y=(h/2)+120"
            f":shadowcolor=black:shadowx=1:shadowy=1",
        ])

        # ===================== LOGO CONFIG =====================
        use_logo = LOGO_ENABLED and LOGO_PATH and os.path.exists(LOGO_PATH)
        logo_xy  = None

        if use_logo:
            margin = 20
            pos_map = {
                "top-left":     f"{margin}:{margin}",
                "top-right":    f"W-w-{margin}:{margin}",
                "bottom-left":  f"{margin}:H-h-{margin}",
                "bottom-right": f"W-w-{margin}:H-h-{margin}",
            }
            logo_xy = pos_map.get(LOGO_POS, f"{margin}:{margin}")

        # ===================== BACKGROUND VIDEO =====================
        bg_file = None
        if BG_SOURCE != "none":
            try:
                bg_file = get_bg_video(
                    word, example, BG_SOURCE, VIDEO_THEME,
                    topic=topic or self.current_topic
                )
            except Exception as e:
                print(f"[BG] Exception: {e}")
                bg_file = None

        # ===================== BUILD FFMPEG COMMAND =====================
        cmd = None

        if bg_file and os.path.exists(bg_file):
            is_gif   = bg_file.endswith(".gif")
            fps      = "15" if is_gif else "25"
            loop_flag = ["-ignore_loop", "0"] if is_gif else []

            vf_full = (
                f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=increase,"
                f"crop={VIDEO_W}:{VIDEO_H},"
                f"format=yuv420p,"
                + vf_text
            )

            if use_logo and logo_xy:
                # ✅ Complex filtergraph: video + text + logo
                complex_filter = (
                    f"[0:v]scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=increase,"
                    f"crop={VIDEO_W}:{VIDEO_H},format=yuv420p,"
                    f"{vf_text}[bg];"
                    f"[2:v]scale={LOGO_SIZE}:-1,format=rgba,"
                    f"colorchannelmixer=aa={LOGO_ALPHA}[logo];"
                    f"[bg][logo]overlay={logo_xy}[out]"
                )
                cmd = (
                    [FFMPEG_PATH, "-y"]
                    + loop_flag
                    + ["-stream_loop", "-1", "-i", bg_file]
                    + ["-i", final_audio]
                    + ["-i", LOGO_PATH]
                    + ["-filter_complex", complex_filter]
                    + ["-map", "[out]", "-map", "1:a"]
                    + ["-t", str(dur), "-r", fps]
                    + ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"]
                    + ["-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100"]
                    + ["-shortest", seg_mp4]
                )
            else:
                # ✅ Không logo - command đơn giản
                cmd = (
                    [FFMPEG_PATH, "-y"]
                    + loop_flag
                    + ["-stream_loop", "-1", "-i", bg_file]
                    + ["-i", final_audio]
                    + ["-vf", vf_full, "-t", str(dur), "-r", fps]
                    + ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "28"]
                    + ["-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100"]
                    + ["-shortest", seg_mp4]
                )

        else:
            # ✅ Fallback: gradient màu (không cần bg video)
            theme    = random.choice(GRADIENT_THEMES)
            bg_color = theme[0]

            if use_logo and logo_xy:
                complex_filter = (
                    f"[0:v]{vf_text}[bg];"
                    f"[1:v]scale={LOGO_SIZE}:-1,format=rgba,"
                    f"colorchannelmixer=aa={LOGO_ALPHA}[logo];"
                    f"[bg][logo]overlay={logo_xy}[out]"
                )
                cmd = [
                    FFMPEG_PATH, "-y",
                    "-f", "lavfi",
                    "-i", f"color=c={bg_color}:s={VIDEO_W}x{VIDEO_H}:d={dur}",
                    "-i", LOGO_PATH,
                    "-i", final_audio,
                    "-filter_complex", complex_filter,
                    "-map", "[out]", "-map", "2:a",
                    "-t", str(dur),
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100",
                    "-shortest", seg_mp4
                ]
            else:
                cmd = [
                    FFMPEG_PATH, "-y",
                    "-f", "lavfi",
                    "-i", f"color=c={bg_color}:s={VIDEO_W}x{VIDEO_H}:d={dur}",
                    "-i", final_audio,
                    "-vf", vf_text,
                    "-t", str(dur),
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100",
                    "-shortest", seg_mp4
                ]

        # ===================== SAFETY CHECK =====================
        if not cmd:
            raise RuntimeError("FFmpeg command chưa được khởi tạo!")

        # ===================== RUN FFMPEG =====================
        r = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # ===================== CLEANUP AUDIO =====================
        for f in audio_parts + [final_audio]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass

        # ===================== CHECK RESULT =====================
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-500:] or "Lỗi render segment")

        return None, seg_mp4

    def concat_segments(self, segs, output, vid_idx):
        list_file = os.path.join(OUTPUT_DIR, f"_list{vid_idx}.txt")
        with open(list_file, "w", encoding="utf-8") as f:
            for s in segs:
                p = os.path.abspath(s).replace("\\", "/")
                f.write(f"file '{p}'\n")
        cmd = [
            FFMPEG_PATH, "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output
        ]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if os.path.exists(list_file):
            os.remove(list_file)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-500:] or "Lỗi ghép video")
        pass

    def process_row(self, row, vid_idx):
        ok, msg = validate_row(row)
        if not ok:
            raise ValueError(msg)

        self.log(f"🎬 Video {vid_idx + 1}: đang render...")
        items = [
            (normalize(row[i]), normalize(row[i+1]), normalize(row[i+2]))
            for i in range(0, 18, 3)
        ]

        segs = []
        try:
            for seg_idx, (word, meaning, example) in enumerate(items, 1):
                if self.stop_event.is_set():
                    return
                self.log(f"  🔊 [{seg_idx}/6] {word} | {meaning}")
                _, seg = self.render_segment(
                    word, meaning, example, vid_idx, seg_idx,
                    topic=self.current_topic
                )
                segs.append(seg)

            out = os.path.join(OUTPUT_DIR, f"vocab_video_{vid_idx + 1:03d}.mp4")
            self.concat_segments(segs, out, vid_idx)
            self.log(f"✅ Xong: vocab_video_{vid_idx + 1:03d}.mp4")

        finally:
            for f in segs:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass

    def worker(self):
        while not self.stop_event.is_set():
            try:
                item = self.queue.get(timeout=0.5)
            except Empty:
                if self.done_count >= self.total:
                    break
                continue
            if item is None:
                self.queue.task_done()
                break
            row, idx = item
            try:
                self.process_row(row, idx)
            except Exception as e:
                self.log(f"❌ Lỗi video {idx + 1}: {e}")
            finally:
                self.done_count += 1
                if self.progress_fn:
                    self.progress_fn()
                self.queue.task_done()
        self.running = False
        if self.done_fn:
            self.done_fn()

    def start(self, rows):
        if self.running:
            raise RuntimeError("Đang chạy, vui lòng chờ hoặc dừng trước")
        self.stop_event.clear()
        self.done_count = 0
        self.total = len(rows)
        self.running = True
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except Exception:
                break
        for idx, row in enumerate(rows):
            self.queue.put((row, idx))
        threading.Thread(target=self.worker, daemon=True).start()

    def stop(self):
        self.stop_event.set()
        self.queue.put(None)



# =====================================================
# CLASS APP - V6 HOÀN CHỈNH
# =====================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1100x820")
        self.root.configure(bg="#f0f4f8")

        self.rows = []
        self.csv_path = tk.StringVar(value=DEFAULT_CSV_FILE)

        self.engine = VideoEngine(
            log_fn=self.safe_log,
            progress_fn=self.safe_progress,
            done_fn=self.on_done
        )

        self._build_ui()
        self.safe_log("🚀 ENGLISH VOCAB FACTORY V2 sẵn sàng!")
        self.safe_log(f"📁 Output: {OUTPUT_DIR}")

    # ==================== BUILD UI ====================
    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        def make_tab(title):
            frame = tk.Frame(nb, bg="#f0f4f8")
            nb.add(frame, text=f"  {title}  ")
            return frame

        self._build_tab_quick_input(make_tab("✏️ Nhập từ"))
        self._build_tab_csv(make_tab("📄 CSV"))
        self._build_tab_render(make_tab("🎬 Render"))
        self._build_tab_voice(make_tab("🎙️ Voice"))
        self._build_tab_background(make_tab("🎥 Background"))
        self._build_tab_logo(make_tab("🖼️ Logo"))
        self._build_tab_ai(make_tab("🤖 AI"))
        self._build_tab_dictionary(make_tab("📚 Dictionary"))
        self._build_tab_posts(make_tab("📰 Bài viết"))
        self._build_tab_system(make_tab("⚙️ System"))

    # ==================== TAB 1: NHẬP TỪ ====================
    def _build_tab_quick_input(self, parent):
        tk.Label(parent, text="📝 Nhập danh sách từ tiếng Anh (mỗi từ 1 dòng)",
                 font=("Segoe UI", 11, "bold"), bg="#f0f4f8").pack(anchor="w", padx=12, pady=(12, 4))
        tk.Label(parent,
                 text="Chương trình sẽ tự tra nghĩa + ví dụ và chia thành nhóm 6 từ → xuất CSV → render video",
                 fg="#6b7280", bg="#f0f4f8").pack(anchor="w", padx=12)

        self.word_input = scrolledtext.ScrolledText(parent, height=12, font=("Consolas", 11))
        self.word_input.pack(fill="both", expand=True, padx=12, pady=8)

        sample_words = "\n".join(["run", "walk", "jump", "climb", "stand", "sit",
                                   "eat", "drink", "sleep", "laugh", "cry", "open",
                                   "dog", "cat", "bird", "fish", "duck", "rabbit"])
        self.word_input.insert("1.0", sample_words)

        btn_frame = tk.Frame(parent, bg="#f0f4f8")
        btn_frame.pack(fill="x", padx=12, pady=6)
        ttk.Button(btn_frame, text="🔍 Xem trước nhóm từ",
                   command=self.preview_groups).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="💾 Xuất ra CSV",
                   command=self.export_to_csv).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="🚀 Xuất CSV + Render ngay",
                   command=self.export_and_render).pack(side="left", padx=4)

        tk.Label(parent, text="👁️ Xem trước:", font=("Segoe UI", 10, "bold"),
                 bg="#f0f4f8").pack(anchor="w", padx=12)
        self.preview_box = scrolledtext.ScrolledText(parent, height=8, font=("Consolas", 10),                                        state="disabled", bg="#1e293b", fg="#94a3b8")
        self.preview_box.pack(fill="x", padx=12, pady=(0, 8))

    # ==================== TAB 2: CSV ====================
    def _build_tab_csv(self, parent):
        tk.Label(parent, text="📄 Quản lý file CSV đầu vào",
                 font=("Segoe UI", 11, "bold"), bg="#f0f4f8").pack(anchor="w", padx=12, pady=(12, 4))

        path_frame = tk.Frame(parent, bg="#f0f4f8")
        path_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(path_frame, text="File CSV:", bg="#f0f4f8").pack(side="left")
        tk.Entry(path_frame, textvariable=self.csv_path, width=60,
                 font=("Consolas", 10)).pack(side="left", padx=6)
        ttk.Button(path_frame, text="📂 Browse", command=self.browse_csv).pack(side="left")

        btn_frame = tk.Frame(parent, bg="#f0f4f8")
        btn_frame.pack(fill="x", padx=12, pady=6)
        ttk.Button(btn_frame, text="✅ Load & Kiểm tra CSV",
                   command=self.load_validate_csv).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="📄 Tạo CSV mẫu",
                   command=self.create_sample_csv).pack(side="left", padx=4)

        tk.Label(parent, text="📋 Nội dung CSV:",
                 font=("Segoe UI", 10, "bold"), bg="#f0f4f8").pack(anchor="w", padx=12, pady=(8, 2))
        self.csv_view = scrolledtext.ScrolledText(parent, height=22, font=("Consolas", 9),                                        state="disabled", bg="#1e293b", fg="#e2e8f0")
        self.csv_view.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    # ==================== TAB 3: RENDER ====================
    def _build_tab_render(self, parent):
        tk.Label(parent, text="🎬 Render Video",
                 font=("Segoe UI", 11, "bold"), bg="#f0f4f8").pack(anchor="w", padx=12, pady=(12, 4))

        info_frame = tk.LabelFrame(parent, text="Thông tin", bg="#f0f4f8")
        info_frame.pack(fill="x", padx=12, pady=6)
        self.info_label = tk.Label(info_frame,
                                   text="Chưa có dữ liệu. Vui lòng load CSV hoặc nhập từ.",
                                   fg="#6b7280", bg="#f0f4f8")
        self.info_label.pack(anchor="w", padx=10, pady=6)

        btn_frame = tk.Frame(parent, bg="#f0f4f8")
        btn_frame.pack(fill="x", padx=12, pady=6)
        self.start_btn = ttk.Button(btn_frame, text="🚀 Bắt đầu Render",
                                    command=self.start_render)
        self.start_btn.pack(side="left", padx=4)
        ttk.Button(btn_frame, text="🛑 Dừng",
                   command=self.stop_render).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="📁 Mở Output",
                   command=self.open_output).pack(side="left", padx=4)

        self.progress = ttk.Progressbar(parent, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=12, pady=6)
        self.progress_label = tk.Label(parent, text="0 / 0", bg="#f0f4f8", fg="#374151")
        self.progress_label.pack(anchor="w", padx=12)

        tk.Label(parent, text="📋 Log:", font=("Segoe UI", 10, "bold"),
                 bg="#f0f4f8").pack(anchor="w", padx=12, pady=(8, 2))
        self.log_box = scrolledtext.ScrolledText(
            parent, height=18, font=("Consolas", 10),
            state="disabled", bg="#0f172a", fg="#94a3b8"
        )
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    # ==================== TAB 4: VOICE ====================
    def _build_tab_voice(self, parent):
        tk.Label(parent, text="🎙️ Voice Settings",
                 font=("Segoe UI", 14, "bold"), bg="#f0f4f8").pack(pady=10)

        mode_frame = tk.LabelFrame(parent, text="Chế độ giọng đọc", bg="#f0f4f8")
        mode_frame.pack(fill="x", padx=20, pady=8)

        self.voice_mode_var = tk.StringVar(value=VOICE_MODE)
        for text, val in [
            ("🔊 Edge TTS (Free, nhanh, ổn định)", "edge"),
            ("🎤 ElevenLabs (giọng xịn, giống TikTok)", "eleven"),
            ("⚡ Hybrid (Word+Example=Eleven, Meaning=Edge)", "hybrid")
        ]:
            tk.Radiobutton(mode_frame, text=text, variable=self.voice_mode_var,
                           value=val, bg="#f0f4f8",
                           font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=4)

        key_frame = tk.LabelFrame(parent, text="ElevenLabs API Key", bg="#f0f4f8")
        key_frame.pack(fill="x", padx=20, pady=8)
        tk.Label(key_frame, text="API Key:", bg="#f0f4f8").grid(
            row=0, column=0, sticky="w", padx=10, pady=6)
        self.eleven_key_var = tk.StringVar(value=ELEVENLABS_API_KEY)
        tk.Entry(key_frame, textvariable=self.eleven_key_var,
                 width=55, show="*").grid(row=0, column=1, padx=6, pady=6)

        ttk.Button(parent, text="💾 Lưu Voice Settings",
                   command=self.save_settings).pack(pady=15)

    # ==================== TAB 5: BACKGROUND ====================
    def _build_tab_background(self, parent):
        tk.Label(parent, text="🎥 Background Video",
                 font=("Segoe UI", 14, "bold"), bg="#f0f4f8").pack(pady=10)

        src_frame = tk.LabelFrame(parent, text="Nguồn video nền", bg="#f0f4f8")
        src_frame.pack(fill="x", padx=20, pady=8)

        self.bg_source_var = tk.StringVar(value=BG_SOURCE)
        for text, val in [
            ("🌟 Pexels (khuyên dùng - video đẹp, miễn phí)", "pexels"),
            ("🖼️ Pixabay (video + GIF đa dạng)", "pixabay"),
            ("😂 Giphy (GIF vui, viral)", "giphy"),
            ("🎥 Mixkit (video cinematic đẹp)", "mixkit"),
            ("🚫 Không dùng (chỉ màu nền)", "none"),
        ]:
            tk.Radiobutton(src_frame, text=text, variable=self.bg_source_var,
                           value=val, bg="#f0f4f8",
                           font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=3)

        key_frame = tk.LabelFrame(parent, text="API Keys", bg="#f0f4f8")
        key_frame.pack(fill="x", padx=20, pady=8)

        # Theme chọn chủ đề video
        theme_frame = tk.LabelFrame(parent, text="🎭 Chủ đề video (Video Theme)", bg="#f0f4f8")
        theme_frame.pack(fill="x", padx=20, pady=8)
        tk.Label(theme_frame,
                 text="Kết hợp từ + chủ đề khi tìm kiếm video nền để tăng sự thu hút",
                 fg="#6b7280", bg="#f0f4f8", font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(4, 6))

        self.video_theme_var = tk.StringVar(value=VIDEO_THEME)
        theme_grid = tk.Frame(theme_frame, bg="#f0f4f8")
        theme_grid.pack(anchor="w", padx=10, pady=(0, 8))
        themes = [
            ("🚫 Không dùng", "none"),
            ("😂 Hài hước",   "funny"),
            ("👶 Trẻ em",     "kids"),
            ("🎯 Nghiêm túc", "serious"),
            ("🌿 Thiên nhiên","nature"),
            ("🎨 Hoạt hình",  "cartoon"),
            ("⚡ Anime",      "anime"),
            ("🏃 Thể thao",   "sport"),
        ]
        for col, (label, val) in enumerate(themes):
            tk.Radiobutton(theme_grid, text=label, variable=self.video_theme_var,
                           value=val, bg="#f0f4f8",
                           font=("Segoe UI", 10)).grid(row=col // 4, column=col % 4, padx=8, pady=2, sticky="w")

        self.pexels_key_var = tk.StringVar(value=PEXELS_API_KEY)
        self.pixabay_key_var = tk.StringVar(value=PIXABAY_API_KEY)
        self.giphy_key_var = tk.StringVar(value=GIPHY_API_KEY)

        for row_idx, (label, var) in enumerate([
            ("Pexels API Key:", self.pexels_key_var),
            ("Pixabay API Key:", self.pixabay_key_var),
            ("Giphy API Key:", self.giphy_key_var),
        ]):
            tk.Label(key_frame, text=label, bg="#f0f4f8").grid(
                row=row_idx, column=0, sticky="w", padx=10, pady=4)
            tk.Entry(key_frame, textvariable=var,
                     width=55, show="*").grid(row=row_idx, column=1, padx=6, pady=4)

        ttk.Button(parent, text="💾 Lưu Background Settings",
                   command=self.save_settings).pack(pady=15)

    # ==================== TAB 6: LOGO ====================
    def _build_tab_logo(self, parent):
        tk.Label(parent, text="🖼️ Logo Overlay",
                 font=("Segoe UI", 14, "bold"), bg="#f0f4f8").pack(pady=10)

        logo_frame = tk.LabelFrame(parent, text="Cài đặt Logo", bg="#f0f4f8")
        logo_frame.pack(fill="x", padx=20, pady=8)

        self.logo_enabled_var = tk.BooleanVar(value=LOGO_ENABLED)
        tk.Checkbutton(logo_frame, text="✅ Bật logo overlay",
                       variable=self.logo_enabled_var,
                       bg="#f0f4f8").grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=4)

        tk.Label(logo_frame, text="File Logo (PNG):", bg="#f0f4f8").grid(
            row=1, column=0, sticky="w", padx=10, pady=4)
        logo_path_frame = tk.Frame(logo_frame, bg="#f0f4f8")
        logo_path_frame.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        self.logo_path_var = tk.StringVar(value=LOGO_PATH)
        tk.Entry(logo_path_frame, textvariable=self.logo_path_var,
                 width=40, font=("Consolas", 9)).pack(side="left")
        ttk.Button(logo_path_frame, text="📂 Browse",
                   command=self._browse_logo).pack(side="left", padx=4)

        tk.Label(logo_frame, text="Kích thước (px):", bg="#f0f4f8").grid(
            row=2, column=0, sticky="w", padx=10, pady=4)
        self.logo_size_var = tk.IntVar(value=LOGO_SIZE)
        tk.Spinbox(logo_frame, from_=30, to=300,
                   textvariable=self.logo_size_var, width=8).grid(
            row=2, column=1, sticky="w", padx=6, pady=4)

        tk.Label(logo_frame, text="Vị trí:", bg="#f0f4f8").grid(
            row=3, column=0, sticky="w", padx=10, pady=4)
        self.logo_pos_var = tk.StringVar(value=LOGO_POS)
        pos_frame = tk.Frame(logo_frame, bg="#f0f4f8")
        pos_frame.grid(row=3, column=1, sticky="w", padx=6, pady=4)
        for label, val in [("↖ Trên trái", "top-left"), ("↗ Trên phải", "top-right"),
                           ("↙ Dưới trái", "bottom-left"), ("↘ Dưới phải", "bottom-right")]:
            tk.Radiobutton(pos_frame, text=label, variable=self.logo_pos_var,
                           value=val, bg="#f0f4f8").pack(side="left", padx=4)

        tk.Label(logo_frame, text="Độ mờ (0-1):", bg="#f0f4f8").grid(
            row=4, column=0, sticky="w", padx=10, pady=4)
        self.logo_alpha_var = tk.DoubleVar(value=LOGO_ALPHA)
        tk.Scale(logo_frame, from_=0.1, to=1.0, resolution=0.05,
                 variable=self.logo_alpha_var, orient="horizontal",
                 length=200, bg="#f0f4f8").grid(row=4, column=1, sticky="w", padx=6, pady=4)

        ttk.Button(parent, text="💾 Lưu Logo Settings",
                   command=self.save_settings).pack(pady=15)

    # ==================== TAB 7: AI ====================
    def _build_tab_ai(self, parent):
        tk.Label(parent, text="🤖 AI Settings",
                 font=("Segoe UI", 14, "bold"), bg="#f0f4f8").pack(pady=10)

        provider_frame = tk.LabelFrame(parent, text="AI Provider", bg="#f0f4f8")
        provider_frame.pack(fill="x", padx=20, pady=8)

        self.ai_provider_var = tk.StringVar(value=AI_PROVIDER)
        for label, val in [("🔌 Offline (từ điển có sẵn)", "offline"),
                            ("✨ Google Gemini", "gemini")]:
            tk.Radiobutton(provider_frame, text=label,
                           variable=self.ai_provider_var,
                           value=val, bg="#f0f4f8",
                           font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=4)

        key_frame = tk.LabelFrame(parent, text="API Keys", bg="#f0f4f8")
        key_frame.pack(fill="x", padx=20, pady=8)
        tk.Label(key_frame, text="Gemini API Key:", bg="#f0f4f8").grid(
            row=0, column=0, sticky="w", padx=10, pady=6)
        self.gemini_key_var = tk.StringVar(value=GEMINI_API_KEY)
        tk.Entry(key_frame, textvariable=self.gemini_key_var,
                 width=60, show="*").grid(row=0, column=1, padx=6, pady=6)

        self.use_online_var = tk.BooleanVar(value=True)
        tk.Checkbutton(parent,
                       text="🌐 Bật tra cứu online (dictionary + google)",
                       variable=self.use_online_var,
                       bg="#f0f4f8").pack(anchor="w", padx=20, pady=6)

        btn_frame = tk.Frame(parent, bg="#f0f4f8")
        btn_frame.pack(fill="x", padx=20, pady=6)
        ttk.Button(btn_frame, text="🧪 Test với từ 'apple'",
                   command=self.test_ai_lookup).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="💾 Lưu AI Settings",
                   command=self.save_ai_settings).pack(side="left", padx=4)

        tk.Label(parent, text="Kết quả test:", bg="#f0f4f8",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=(8, 2))
        self.ai_test_box = scrolledtext.ScrolledText(
            parent, height=10, font=("Consolas", 10),
            state="disabled", bg="#0f172a", fg="#94a3b8"
        )
        self.ai_test_box.pack(fill="both", expand=True, padx=20, pady=(0, 8))

    # ==================== TAB 8: DICTIONARY ====================
    def _build_tab_dictionary(self, parent):
        tk.Label(parent, text="📚 Dictionary Manager",
                 font=("Segoe UI", 14, "bold"), bg="#f0f4f8").pack(pady=20)

        tk.Label(parent,
                 text="Thêm / sửa / xóa từ vựng trong thư viện offline",
                 fg="#6b7280", bg="#f0f4f8",
                 font=("Segoe UI", 10)).pack()

        ttk.Button(parent,
                   text="🚀 Mở trình quản lý từ điển",
                   command=self.open_dict_manager).pack(pady=20)

        stats_frame = tk.LabelFrame(parent, text="📊 Thống kê từ điển", bg="#f0f4f8")
        stats_frame.pack(fill="x", padx=20, pady=8)

        try:
            d = get_dict()
            stats = d.get_stats()
            tk.Label(stats_frame,
                     text=f"Tổng nhóm: {stats['total_groups']}   |   Tổng từ: {stats['total_words']}",
                     bg="#f0f4f8", font=("Segoe UI", 11)).pack(pady=8)
            for group, count in stats["groups"].items():
                tk.Label(stats_frame,
                         text=f"  • {group}: {count} từ",
                         bg="#f0f4f8", fg="#374151").pack(anchor="w", padx=20)
        except Exception:
            tk.Label(stats_frame, text="Chưa load được từ điển",
                     bg="#f0f4f8", fg="#ef4444").pack(pady=8)

    # ==================== TAB 10: BÀI VIẾT ====================
    def _build_tab_posts(self, parent):
        PostManagerTab(parent, self)

    # ==================== TAB 9: SYSTEM ====================
    def _build_tab_system(self, parent):
        tk.Label(parent, text="⚙️ System",
                 font=("Segoe UI", 14, "bold"), bg="#f0f4f8").pack(pady=10)

        check_frame = tk.LabelFrame(parent, text="Kiểm tra hệ thống", bg="#f0f4f8")
        check_frame.pack(fill="x", padx=20, pady=8)

        btn_row = tk.Frame(check_frame, bg="#f0f4f8")
        btn_row.pack(fill="x", padx=10, pady=8)
        ttk.Button(btn_row, text="✅ Kiểm tra FFmpeg",
                   command=lambda: messagebox.showinfo("FFmpeg", check_ffmpeg()[1])
                   ).pack(side="left", padx=4)
        ttk.Button(btn_row, text="📁 Mở Output",
                   command=self.open_output).pack(side="left", padx=4)

        exe_frame = tk.LabelFrame(parent, text="📦 Build .EXE", bg="#f0f4f8")
        exe_frame.pack(fill="x", padx=20, pady=8)

        tk.Label(exe_frame,
                 text="Dùng PyInstaller để đóng gói thành file .exe",
                 bg="#f0f4f8").pack(anchor="w", padx=10, pady=4)

        btn2 = tk.Frame(exe_frame, bg="#f0f4f8")
        btn2.pack(fill="x", padx=10, pady=6)
        ttk.Button(btn2, text="📦 Cài PyInstaller",
                   command=self.install_pyinstaller).pack(side="left", padx=4)
        ttk.Button(btn2, text="🔨 Build .EXE",
                   command=self.build_exe).pack(side="left", padx=4)

        self.exe_log = scrolledtext.ScrolledText(
            parent, height=12, font=("Consolas", 10),
            state="disabled", bg="#0f172a", fg="#94a3b8"
        )
        self.exe_log.pack(fill="both", expand=True, padx=20, pady=(0, 8))

    # ==================== SAFE UI UPDATES ====================
    def safe_log(self, msg):
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def safe_progress(self):
        self.root.after(0, self._step_progress)

    def _step_progress(self):
        val = self.progress["value"] + 1
        self.progress["value"] = min(val, self.progress["maximum"])
        done = int(self.progress["value"])
        total = int(self.progress["maximum"])
        self.progress_label.config(text=f"{done} / {total} video")

    def on_done(self):
        self.root.after(0, self._on_done_ui)

    def _on_done_ui(self):
        self.start_btn.config(state="normal")
        self.safe_log("🏁 Hoàn tất toàn bộ tiến trình render!")

    # ==================== TAB 1 METHODS ====================
    def _get_word_list(self):
        raw = self.word_input.get("1.0", "end").strip()
        return [w.strip() for w in raw.splitlines() if w.strip()]

    def _get_groups(self):
        words = self._get_word_list()
        return auto_split_words(words, group_size=6) if words else []

    def preview_groups(self):
        groups = self._get_groups()
        if not groups:
            messagebox.showwarning("Trống", "Chưa có từ nào để xem trước!")
            return
        self.preview_box.config(state="normal")
        self.preview_box.delete("1.0", "end")
        for i, group in enumerate(groups, 1):
            self.preview_box.insert("end", f"--- Video {i} ---\n")
            for j, word in enumerate(group, 1):
                self.preview_box.insert("end", f"  [{j}] {word}\n")
            self.preview_box.insert("end", "\n")
        self.preview_box.config(state="disabled")
        self.safe_log(f"👁️ Xem trước: {len(groups)} nhóm từ")

    def export_to_csv(self):
        groups = self._get_groups()
        if not groups:
            messagebox.showwarning("Trống", "Chưa có từ nào để xuất!")
            return

        save_path = filedialog.asksaveasfilename(
            title="Lưu file CSV", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")], initialfile="data.csv"
        )
        if not save_path:
            return

        def run():
            try:
                self.safe_log(f"⏳ Đang tra nghĩa {len(groups)} nhóm từ...")
                rows = [build_row_from_words(g) for g in groups]
                with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
                    csv.writer(f).writerows(rows)
                self.rows = rows
                self.root.after(0, self.csv_path.set, save_path)
                self.root.after(0, self._update_csv_view, rows)
                self.root.after(0, self._update_info_label)
                self.safe_log(f"💾 Đã xuất CSV: {save_path} ({len(rows)} dòng)")
                self.root.after(0, lambda: messagebox.showinfo(
                    "Thành công", f"Đã xuất {len(rows)} dòng vào:\n{save_path}"))
            except Exception as e:
                self.safe_log(f"❌ Lỗi xuất CSV: {e}")

        threading.Thread(target=run, daemon=True).start()

    def export_and_render(self):
        groups = self._get_groups()
        if not groups:
            messagebox.showwarning("Trống", "Chưa có từ nào!")
            return

        save_path = filedialog.asksaveasfilename(
            title="Lưu file CSV trước khi render", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")], initialfile="data.csv"
        )
        if not save_path:
            return

        def run():
            try:
                self.safe_log(f"⏳ Đang tra nghĩa {len(groups)} nhóm từ...")
                rows = [build_row_from_words(g) for g in groups]
                with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
                    csv.writer(f).writerows(rows)
                self.rows = rows
                self.root.after(0, self.csv_path.set, save_path)
                self.root.after(0, self._update_csv_view, rows)
                self.root.after(0, self._update_info_label)
                self.safe_log(f"💾 Đã xuất CSV: {save_path}")
                self.root.after(0, self.start_render)
            except Exception as e:
                self.safe_log(f"❌ Lỗi: {e}")

        threading.Thread(target=run, daemon=True).start()

    # ==================== TAB 2 METHODS ====================
    def browse_csv(self):
        path = filedialog.askopenfilename(
            title="Chọn file CSV", filetypes=[("CSV files", "*.csv")])
        if path:
            self.csv_path.set(path)

    def load_validate_csv(self):
        path = self.csv_path.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("Lỗi", f"Không tìm thấy file:\n{path}")
            return
        ok, msg, rows = validate_csv(path)
        if not ok:
            messagebox.showerror("CSV lỗi", msg)
            self.safe_log(f"❌ {msg}")
            return
        self.rows = rows
        self._update_csv_view(rows)
        self._update_info_label()
        self.safe_log(f"✅ Load CSV thành công: {msg}")
        messagebox.showinfo("Hợp lệ", msg)

    def create_sample_csv(self):
        save_path = filedialog.asksaveasfilename(
            title="Lưu CSV mẫu", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")], initialfile="data_sample.csv"
        )
        if not save_path:
            return

        def run():
            sample_words = ["run", "walk", "jump", "climb", "stand", "sit",
                            "eat", "drink", "sleep", "laugh", "cry", "open",
                            "dog", "cat", "bird", "fish", "duck", "rabbit"]
            groups = auto_split_words(sample_words, 6)
            rows = [build_row_from_words(g) for g in groups]
            try:
                with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
                    csv.writer(f).writerows(rows)
                self.rows = rows
                self.root.after(0, self.csv_path.set, save_path)
                self.root.after(0, self._update_csv_view, rows)
                self.root.after(0, self._update_info_label)
                self.safe_log(f"📄 Đã tạo CSV mẫu: {save_path}")
                self.root.after(0, lambda: messagebox.showinfo(
                    "Thành công", f"Đã tạo file mẫu:\n{save_path}"))
            except Exception as e:
                self.safe_log(f"❌ Lỗi tạo CSV mẫu: {e}")

        threading.Thread(target=run, daemon=True).start()

    def _update_csv_view(self, rows):
        self.csv_view.config(state="normal")
        self.csv_view.delete("1.0", "end")
        for i, row in enumerate(rows, 1):
            words_only = [row[j * 3] for j in range(6)]
            self.csv_view.insert("end", f"[{i:03d}] {' | '.join(words_only)}\n")
        self.csv_view.config(state="disabled")

    def _update_info_label(self):
        count = len(self.rows)
        self.info_label.config(
            text=f"✅ Sẵn sàng render {count} video ({count * 6} từ vựng)",
            fg="#059669"
        )
        self.progress["maximum"] = count
        self.progress["value"] = 0
        self.progress_label.config(text=f"0 / {count} video")

    # ==================== TAB 3 METHODS ====================
    def start_render(self):
        ok, msg = check_ffmpeg()
        if not ok:
            messagebox.showerror("Thiếu FFmpeg", msg)
            return
        if not self.rows:
            messagebox.showwarning("Chưa có dữ liệu",
                                   "Vui lòng nhập từ hoặc load CSV trước!")
            return
        ensure_output_dir()
        self.progress["maximum"] = len(self.rows)
        self.progress["value"] = 0
        self.progress_label.config(text=f"0 / {len(self.rows)} video")
        try:
            self.engine.start(self.rows)
            self.start_btn.config(state="disabled")
            self.safe_log(f"🚀 Bắt đầu render {len(self.rows)} video...")
            self.safe_log(f"📁 Output: {OUTPUT_DIR}")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def stop_render(self):
        self.engine.stop()
        self.start_btn.config(state="normal")
        self.safe_log("🛑 Đã gửi lệnh dừng")

    def open_output(self):
        ensure_output_dir()
        try:
            os.startfile(OUTPUT_DIR)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    # ==================== SYSTEM METHODS ====================
    def _exe_log(self, msg):
        self.root.after(0, self.__exe_log_safe, msg)

    def __exe_log_safe(self, msg):
        self.exe_log.config(state="normal")
        self.exe_log.insert("end", msg + "\n")
        self.exe_log.see("end")
        self.exe_log.config(state="disabled")

    def install_pyinstaller(self):
        def run():
            self._exe_log("📦 Đang cài PyInstaller...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "pyinstaller"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            self._exe_log(result.stdout)
            if result.returncode == 0:
                self._exe_log("✅ Cài PyInstaller thành công!")
            else:
                self._exe_log(f"❌ Lỗi: {result.stderr}")
        threading.Thread(target=run, daemon=True).start()

    def build_exe(self):
        script_path = os.path.abspath(sys.argv[0])
        if not os.path.exists(script_path):
            messagebox.showerror("Lỗi", f"Không tìm thấy file script:\n{script_path}")
            return

        def run():
            self._exe_log(f"🔨 Đang build EXE từ: {script_path}")
            self._exe_log("⏳ Quá trình này có thể mất 1-3 phút...")
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--onefile", "--windowed",
                "--name", "VocabVideoFactory",
                script_path
            ]
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, cwd=BASE_DIR
            )
            if result.returncode == 0:
                exe_path = os.path.join(BASE_DIR, "dist", "VocabVideoFactory.exe")
                self._exe_log("✅ Build thành công!")
                self._exe_log(f"📁 File EXE: {exe_path}")
                self.root.after(0, lambda: messagebox.showinfo(
                    "Build thành công",
                    f"File EXE tại:\n{exe_path}\n\n"
                    "Nhớ copy ffmpeg.exe vào cùng thư mục với EXE!"
                ))
            else:
                self._exe_log("❌ Build thất bại!")
                self._exe_log(result.stderr[-1000:])
        threading.Thread(target=run, daemon=True).start()

    # ==================== AI METHODS ====================
    def test_ai_lookup(self):
        def run():
            self._ai_log("🧪 Đang test với từ 'apple'...")
            meaning, example, source = ai_lookup_word(
                "apple",
                provider=self.ai_provider_var.get(),
                gemini_key=self.gemini_key_var.get().strip()
            )
            self._ai_log(f"✅ Nguồn: {source}")
            self._ai_log(f"   Nghĩa: {meaning}")
            self._ai_log(f"   Ví dụ: {example}")
        threading.Thread(target=run, daemon=True).start()

    def save_ai_settings(self):
        global AI_PROVIDER, GEMINI_API_KEY
        AI_PROVIDER = self.ai_provider_var.get()
        GEMINI_API_KEY = self.gemini_key_var.get().strip()
        self._ai_log(f"💾 Đã lưu! Provider: {AI_PROVIDER}")
        messagebox.showinfo("Đã lưu", f"Provider: {AI_PROVIDER}")

    def _ai_log(self, msg):
        self.root.after(0, self.__ai_log_safe, msg)

    def __ai_log_safe(self, msg):
        self.ai_test_box.config(state="normal")
        self.ai_test_box.insert("end", msg + "\n")
        self.ai_test_box.see("end")
        self.ai_test_box.config(state="disabled")

    # ==================== SETTINGS SAVE ====================
    def save_settings(self):
        global VOICE_MODE, BG_SOURCE, VIDEO_THEME
        global PEXELS_API_KEY, PIXABAY_API_KEY, GIPHY_API_KEY
        global ELEVENLABS_API_KEY
        global LOGO_ENABLED, LOGO_PATH, LOGO_SIZE, LOGO_POS, LOGO_ALPHA

        VOICE_MODE          = self.voice_mode_var.get()
        BG_SOURCE           = self.bg_source_var.get()
        VIDEO_THEME         = self.video_theme_var.get()
        PEXELS_API_KEY      = self.pexels_key_var.get().strip()
        PIXABAY_API_KEY     = self.pixabay_key_var.get().strip()
        GIPHY_API_KEY       = self.giphy_key_var.get().strip()
        ELEVENLABS_API_KEY  = self.eleven_key_var.get().strip()
        LOGO_ENABLED        = self.logo_enabled_var.get()
        LOGO_PATH           = self.logo_path_var.get().strip()
        LOGO_SIZE           = self.logo_size_var.get()
        LOGO_POS            = self.logo_pos_var.get()
        LOGO_ALPHA          = self.logo_alpha_var.get()

        messagebox.showinfo("Đã lưu", 
            f"✅ Voice: {VOICE_MODE}\n"
            f"✅ Background: {BG_SOURCE}\n"
            f"✅ Logo: {'Bật' if LOGO_ENABLED else 'Tắt'}")

    # ==================== LOGO BROWSE ====================
    def _browse_logo(self):
        path = filedialog.askopenfilename(
            title="Chọn file Logo",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if path:
            self.logo_path_var.set(path)

    # ==================== DICT MANAGER ====================
    def open_dict_manager(self):
        open_dict_manager_window(parent=self.root)
        self.safe_log("📚 Đã mở Dictionary Manager")


# =========================================================
# MAIN
# =========================================================
def debug_bg_video(word="duck", example="The duck swims in the pond."):
    """Test toàn bộ pipeline lấy video background với smart keyword"""
    import traceback

    print(f"\n{'='*50}")
    print(f"🔍 DEBUG: get_bg_video(word='{word}', theme='{VIDEO_THEME}', src='{BG_SOURCE}')")
    kw_chain = build_smart_keywords(word, example, VIDEO_THEME)
    print(f"🔑 Keyword chain: {kw_chain}")
    print(f"{'='*50}")

    # Step 1: Kiểm tra API key
    print(f"\n[1] API Keys:")
    print(f"    PEXELS  : {'✅ Có' if PEXELS_API_KEY else '❌ Trống'} ({PEXELS_API_KEY[:10] if PEXELS_API_KEY else ''}...)")
    print(f"    PIXABAY : {'✅ Có' if PIXABAY_API_KEY else '❌ Trống'}")
    print(f"    GIPHY   : {'✅ Có' if GIPHY_API_KEY else '❌ Trống'}")
    print(f"    BG_SOURCE: {BG_SOURCE}")

    # Step 2: Kiểm tra thư mục cache
    print(f"\n[2] Cache dir: {BG_VIDEO_DIR}")
    ensure_bg_dir()
    print(f"    Tồn tại: {'✅' if os.path.exists(BG_VIDEO_DIR) else '❌'}")

    # Step 3: Fetch URL
    print(f"\n[3] Fetch URL từ {BG_SOURCE}...")
    try:
        if BG_SOURCE == "pexels":
            url = fetch_pexels_video(keyword)
        elif BG_SOURCE == "pixabay":
            url = fetch_pixabay_video(keyword)
        elif BG_SOURCE == "giphy":
            url = fetch_giphy_gif(keyword)
        else:
            url = None

        if url:
            print(f"    ✅ URL: {url[:80]}...")
        else:
            print(f"    ❌ Không lấy được URL (trả về None)")
            return
    except Exception as e:
        print(f"    ❌ Exception: {e}")
        traceback.print_exc()
        return

    # Step 4: Download
    safe_kw = keyword.lower().replace(" ", "_")[:20]
    ext = "gif" if BG_SOURCE == "giphy" else "mp4"
    cache_path = os.path.join(BG_VIDEO_DIR, f"{BG_SOURCE}_{safe_kw}.{ext}")
    print(f"\n[4] Download về: {cache_path}")
    try:
        ok = download_bg_file(url, cache_path)
        if ok:
            size = os.path.getsize(cache_path)
            print(f"    ✅ Download OK! Size: {size:,} bytes")
        else:
            print(f"    ❌ Download thất bại")
    except Exception as e:
        print(f"    ❌ Exception khi download: {e}")
        traceback.print_exc()
def main():
    ensure_output_dir()
    # debug_bg_video("dog") 
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
