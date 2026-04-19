import os
import sys
import csv
import json
import random
import threading
import subprocess
import urllib.request
import urllib.error
from queue import Queue, Empty

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

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

# =========================================================
# AI CONFIG
# =========================================================
AI_PROVIDER = "offline"
GEMINI_API_KEY = "AIzaSyCzVQJOuQBq3PrVq6QmZSYW0p3vEBZyRz4"
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

PROMPT_TEMPLATE = """Bạn là từ điển tiếng Anh - tiếng Việt.
Cho từ tiếng Anh: "{word}"
Hãy trả về JSON theo đúng định dạng sau (không giải thích thêm):
{{"meaning": "nghĩa tiếng Việt ngắn gọn", "example": "1 câu ví dụ tiếng Anh đơn giản dưới 10 từ"}}"""

# =========================================================
# MINI DICT OFFLINE
# =========================================================
MINI_DICT = {
    "run": ("chạy", "I run every morning."),
    "walk": ("đi bộ", "She walks to school."),
    "jump": ("nhảy", "The kids jump high."),
    "eat": ("ăn", "I eat breakfast."),
    "drink": ("uống", "Drink some water."),
    "sleep": ("ngủ", "The baby is sleeping."),
    "read": ("đọc", "I read a book."),
    "write": ("viết", "Write your name."),
    "swim": ("bơi", "Fish swim in water."),
    "sing": ("hát", "She sings beautifully."),
    "dance": ("nhảy múa", "They dance together."),
    "draw": ("vẽ", "I draw a cat."),
    "play": ("chơi", "Children play outside."),
    "study": ("học", "I study every day."),
    "listen": ("nghe", "Listen to the music."),
    "speak": ("nói", "Speak clearly please."),
    "cook": ("nấu ăn", "Mom cooks dinner."),
    "clean": ("dọn dẹp", "Clean your room."),
    "open": ("mở", "Open the door."),
    "close": ("đóng", "Close the window."),
    "push": ("đẩy", "Push the button."),
    "pull": ("kéo", "Pull the handle."),
    "throw": ("ném", "Throw the ball."),
    "catch": ("bắt", "Catch the ball."),
    "cut": ("cắt", "Cut the paper."),
    "climb": ("leo trèo", "Cats climb trees."),
    "stand": ("đứng", "Please stand up."),
    "sit": ("ngồi", "Sit down on the chair."),
    "stop": ("dừng lại", "Stop the car."),
    "cry": ("khóc", "Do not cry."),
    "laugh": ("cười", "They laugh loudly."),
    "dog": ("con chó", "I have a dog."),
    "cat": ("con mèo", "The cat is cute."),
    "bird": ("con chim", "A bird is flying."),
    "fish": ("con cá", "Fish live in water."),
    "duck": ("con vịt", "The duck can swim."),
    "rabbit": ("con thỏ", "The rabbit jumps fast."),
    "lion": ("sư tử", "The lion roars."),
    "tiger": ("hổ", "The tiger is strong."),
    "elephant": ("voi", "The elephant is big."),
    "monkey": ("khỉ", "The monkey climbs."),
    "bear": ("gấu", "A bear eats honey."),
    "horse": ("con ngựa", "Ride a horse."),
    "cow": ("con bò", "The cow eats grass."),
    "pig": ("con lợn", "The pig is pink."),
    "sheep": ("con cừu", "The sheep is white."),
    "goat": ("con dê", "A goat climbs rocks."),
    "frog": ("con ếch", "The frog jumps."),
    "snake": ("con rắn", "The snake crawls."),
    "giraffe": ("hươu cao cổ", "The giraffe is tall."),
    "chicken": ("con gà", "The chicken lays eggs."),
    "apple": ("quả táo", "I eat an apple."),
    "banana": ("quả chuối", "Monkeys love bananas."),
    "orange": ("quả cam", "The orange is sweet."),
    "water": ("nước", "Drink clean water."),
    "milk": ("sữa", "I drink milk daily."),
    "bread": ("bánh mì", "I eat bread for breakfast."),
    "rice": ("cơm", "We eat rice every day."),
    "book": ("quyển sách", "I read a book."),
    "pen": ("bút", "Use a pen to write."),
    "table": ("cái bàn", "Put it on the table."),
    "chair": ("cái ghế", "Sit on the chair."),
    "house": ("ngôi nhà", "I live in a house."),
    "school": ("trường học", "I go to school."),
    "tree": ("cái cây", "The tree is tall."),
    "flower": ("bông hoa", "The flower is beautiful."),
    "sun": ("mặt trời", "The sun is bright."),
    "moon": ("mặt trăng", "The moon shines at night."),
    "star": ("ngôi sao", "Stars shine at night."),
    "rain": ("mưa", "It rains today."),
    "wind": ("gió", "The wind blows."),
    "fire": ("lửa", "Fire is hot."),
    "happy": ("vui vẻ", "I am happy today."),
    "sad": ("buồn", "She looks sad."),
    "big": ("to lớn", "The elephant is big."),
    "small": ("nhỏ bé", "The ant is small."),
    "fast": ("nhanh", "The car is fast."),
    "slow": ("chậm", "The turtle is slow."),
    "hot": ("nóng", "The soup is hot."),
    "cold": ("lạnh", "The ice is cold."),
    "red": ("màu đỏ", "The apple is red."),
    "blue": ("màu xanh dương", "The sky is blue."),
    "green": ("màu xanh lá", "The grass is green."),
    "yellow": ("màu vàng", "The sun is yellow."),
    "white": ("màu trắng", "Snow is white."),
    "black": ("màu đen", "The night is black."),
}

# =========================================================
# AI LOOKUP
# =========================================================
def _call_gemini(word, api_key):
    prompt = PROMPT_TEMPLATE.format(word=word)
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
    return result["meaning"], result["example"]


def lookup_word_offline(word):
    key = word.strip().lower()
    if key in MINI_DICT:
        return MINI_DICT[key]
    return f"[{word}]", f"This is {word}."


def ai_lookup_word(word, provider=None, gemini_key=None):
    p = provider or AI_PROVIDER
    gk = gemini_key or GEMINI_API_KEY
    try:
        if p == "gemini" and gk:
            meaning, example = _call_gemini(word, gk)
            return meaning, example, "gemini"
    except Exception:
        pass
    meaning, example = lookup_word_offline(word)
    return meaning, example, "offline"


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
        ("[", "\$$"),
        ("]", "\$$"),
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

    def render_segment(self, word, meaning, example, vid_idx, seg_idx):
        ensure_output_dir()
        wav = os.path.join(OUTPUT_DIR, f"_a{vid_idx}_{seg_idx}.wav")
        seg = os.path.join(OUTPUT_DIR, f"_s{vid_idx}_{seg_idx}.mp4")

        speech = f"{word}. {meaning}. Example: {example}"
        self.make_voice(speech, wav)
        dur = self.get_duration(wav)

        theme = random.choice(GRADIENT_THEMES)
        bg_color = theme[0]

        w_text = safe_ffmpeg_text(word.upper())
        m_text = safe_ffmpeg_text(f"({meaning})")
        e_text = safe_ffmpeg_text(example)
        counter_text = safe_ffmpeg_text(f"{seg_idx}/6")

        vf_parts = [
            f"drawtext=fontfile='{FONT_PATH}':text='{counter_text}':fontcolor=white@0.5:fontsize=32:x=w-text_w-30:y=30",
            f"drawtext=fontfile='{FONT_PATH}':text='{w_text}':fontcolor=#FFD700:fontsize=80:x=(w-text_w)/2:y=(h/2)-120:shadowcolor=black:shadowx=3:shadowy=3",
            f"drawtext=fontfile='{FONT_PATH}':text='{m_text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h/2)+10:shadowcolor=black:shadowx=2:shadowy=2",
            f"drawtext=fontfile='{FONT_PATH}':text='{e_text}':fontcolor=#cccccc:fontsize=34:x=(w-text_w)/2:y=(h/2)+90:shadowcolor=black:shadowx=1:shadowy=1",
        ]
        vf = ",".join(vf_parts)

        cmd = [
            FFMPEG_PATH, "-y",
            "-f", "lavfi",
            "-i", f"color=c={bg_color}:s={VIDEO_W}x{VIDEO_H}:d={dur}",
            "-i", wav,
            "-vf", vf,
            "-shortest",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            seg
        ]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-500:] or "Lỗi render segment")
        return wav, seg

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

    def process_row(self, row, vid_idx):
        ok, msg = validate_row(row)
        if not ok:
            raise ValueError(msg)
        self.log(f"🎬 Video {vid_idx + 1}: đang render...")
        items = [(normalize(row[i]), normalize(row[i+1]), normalize(row[i+2]))
                 for i in range(0, 18, 3)]
        wavs, segs = [], []
        try:
            for seg_idx, (word, meaning, example) in enumerate(items, 1):
                if self.stop_event.is_set():
                    return
                self.log(f"  🔊 [{seg_idx}/6] {word}")
                wav, seg = self.render_segment(word, meaning, example, vid_idx, seg_idx)
                wavs.append(wav)
                segs.append(seg)
            out = os.path.join(OUTPUT_DIR, f"vocab_video_{vid_idx + 1:03d}.mp4")
            self.concat_segments(segs, out, vid_idx)
            self.log(f"✅ Xong: vocab_video_{vid_idx + 1:03d}.mp4")
        finally:
            for f in wavs + segs:
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


# =========================================================
# GUI
# =========================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1050x820")
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

    def _build_ui(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        tab1 = tk.Frame(nb, bg="#f0f4f8")
        nb.add(tab1, text="  ✏️ Nhập từ nhanh  ")
        self._build_tab_quick_input(tab1)

        tab2 = tk.Frame(nb, bg="#f0f4f8")
        nb.add(tab2, text="  📄 Quản lý CSV  ")
        self._build_tab_csv(tab2)

        tab3 = tk.Frame(nb, bg="#f0f4f8")
        nb.add(tab3, text="  🎬 Render Video  ")
        self._build_tab_render(tab3)

        tab4 = tk.Frame(nb, bg="#f0f4f8")
        nb.add(tab4, text="  📦 Xuất .EXE  ")
        self._build_tab_exe(tab4)

        tab5 = tk.Frame(nb, bg="#f0f4f8")
        nb.add(tab5, text="  🤖 Cài đặt AI  ")
        self._build_tab_ai_settings(tab5)

    # ---- TAB 1 ----
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

    # ---- TAB 2 ----
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

    # ---- TAB 3 ----
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
        tk.Label(parent, text="📋 Log:", font=("Segoe UI", 10, "bold"), bg="#f0f4f8").pack(anchor="w", padx=12, pady=(8, 2))

        self.log_box = scrolledtext.ScrolledText(
            parent, height=18, font=("Consolas", 10),
            state="disabled", bg="#0f172a", fg="#94a3b8"
        )
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    # ---- TAB 4: EXE ----
    def _build_tab_exe(self, parent):
        tk.Label(parent, text="📦 Đóng gói thành file .EXE",
                 font=("Segoe UI", 11, "bold"), bg="#f0f4f8").pack(anchor="w", padx=12, pady=(12, 4))

        info = (
            "Chương trình sẽ dùng PyInstaller để đóng gói toàn bộ thành 1 file .exe\n"
            "Yêu cầu: pip install pyinstaller\n"
            "File .exe sẽ xuất hiện trong thư mục dist/"
        )
        tk.Label(parent, text=info, justify="left", fg="#374151",
                 bg="#f0f4f8", font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=6)

        btn_frame = tk.Frame(parent, bg="#f0f4f8")
        btn_frame.pack(fill="x", padx=12, pady=8)
        ttk.Button(btn_frame, text="📦 Cài PyInstaller",
                   command=self.install_pyinstaller).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="🔨 Build .EXE ngay",
                   command=self.build_exe).pack(side="left", padx=4)

        self.exe_log = scrolledtext.ScrolledText(
            parent, height=22, font=("Consolas", 10),
            state="disabled", bg="#0f172a", fg="#94a3b8"
        )
        self.exe_log.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    # ---- TAB 5: AI SETTINGS ----
    def _build_tab_ai_settings(self, parent):
        tk.Label(parent, text="🤖 Cài đặt AI sinh nghĩa + ví dụ",
                 font=("Segoe UI", 11, "bold"), bg="#f0f4f8").pack(anchor="w", padx=12, pady=(12, 4))

        provider_frame = tk.LabelFrame(parent, text="Chọn AI Provider", bg="#f0f4f8")
        provider_frame.pack(fill="x", padx=12, pady=8)

        self.ai_provider_var = tk.StringVar(value=AI_PROVIDER)
        for label, val in [("🔌 Offline (từ điển có sẵn)", "offline"),
                            ("✨ Google Gemini", "gemini")]:
            tk.Radiobutton(provider_frame, text=label, variable=self.ai_provider_var,
                           value=val, bg="#f0f4f8", font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=4)

        key_frame = tk.LabelFrame(parent, text="API Keys", bg="#f0f4f8")
        key_frame.pack(fill="x", padx=12, pady=8)

        tk.Label(key_frame, text="Gemini API Key:", bg="#f0f4f8").grid(
            row=0, column=0, sticky="w", padx=10, pady=6)
        self.gemini_key_var = tk.StringVar(value=GEMINI_API_KEY)
        tk.Entry(key_frame, textvariable=self.gemini_key_var,
                 width=60, show="*").grid(row=0, column=1, padx=6, pady=6)

        btn_frame = tk.Frame(parent, bg="#f0f4f8")
        btn_frame.pack(fill="x", padx=12, pady=6)
        ttk.Button(btn_frame, text="🧪 Test với từ 'apple'",
                   command=self.test_ai_lookup).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="💾 Lưu cài đặt",
                   command=self.save_ai_settings).pack(side="left", padx=4)

        tk.Label(parent, text="Kết quả test:", bg="#f0f4f8",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
        self.ai_test_box = scrolledtext.ScrolledText(
            parent, height=12, font=("Consolas", 10),
            state="disabled", bg="#0f172a", fg="#94a3b8"
        )
        self.ai_test_box.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    # =========================================================
    # SAFE UI UPDATES
    # =========================================================
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

    # =========================================================
    # TAB 1 METHODS
    # =========================================================
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

    # =========================================================
    # TAB 2 METHODS
    # =========================================================
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

    # =========================================================
    # TAB 3 METHODS
    # =========================================================
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

    # =========================================================
    # TAB 4 METHODS
    # =========================================================
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

    # =========================================================
    # TAB 5 METHODS
    # =========================================================
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


# =========================================================
# MAIN
# =========================================================
def main():
    ensure_output_dir()
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
