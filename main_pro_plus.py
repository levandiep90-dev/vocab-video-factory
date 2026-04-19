import os
import sys
import csv
import random
import threading
import subprocess
from queue import Queue, Empty

import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


# =========================================================
# CONFIG
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")
DEFAULT_CSV_FILE = os.path.join(BASE_DIR, "data.csv")
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg.exe")

# Nên để arial.ttf có sẵn trong Windows
FONT_PATH = "C\\:/Windows/Fonts/arial.ttf"

VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
VIDEO_BG_COLORS = [
    "#0f172a", "#111827", "#1e293b", "#3b0764", "#1f2937", "#172554"
]

APP_TITLE = "ENGLISH VOCAB VIDEO FACTORY"


# =========================================================
# HELPER FUNCTIONS
# =========================================================
def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def check_ffmpeg():
    if not os.path.exists(FFMPEG_PATH):
        return False, f"Không tìm thấy ffmpeg.exe tại:\n{FFMPEG_PATH}"
    return True, "FFmpeg sẵn sàng ✅"


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def safe_ps_text(text):
    """
    Escape text an toàn hơn cho PowerShell
    """
    text = str(text)
    text = text.replace("`", "``")
    text = text.replace('"', '`"')
    text = text.replace("$", "`$")
    return text


def safe_ffmpeg_text(text):
    """
    Escape text cho drawtext của FFmpeg
    """
    text = str(text)
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\\'")
    text = text.replace("%", "\\%")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\$$")
    text = text.replace(",", "\\,")
    return text

def random_bg():
    return random.choice(VIDEO_BG_COLORS)


def validate_row_18_columns(row):
    if not isinstance(row, (list, tuple)):
        return False, "Dữ liệu dòng không phải list/tuple"
    if len(row) != 18:
        return False, f"Dòng phải có đúng 18 cột, hiện tại là {len(row)}"
    for i, value in enumerate(row):
        if normalize_text(value) == "":
            return False, f"Cột thứ {i + 1} đang bị rỗng"
    return True, "OK"


def validate_csv_file(file_path):
    try:
        df = pd.read_csv(file_path, header=None, encoding="utf-8-sig")
    except Exception as e:
        return False, f"Không đọc được file CSV: {e}", None

    if df.empty:
        return False, "File CSV đang rỗng", None

    for idx, row in df.iterrows():
        row_values = row.tolist()
        ok, msg = validate_row_18_columns(row_values)
        if not ok:
            return False, f"Lỗi tại dòng {idx + 1}: {msg}", None

    return True, f"CSV hợp lệ, có {len(df)} dòng", df


def create_csv_from_rows(rows, output_file=DEFAULT_CSV_FILE):
    if not isinstance(rows, list) or len(rows) == 0:
        raise ValueError("rows phải là list và không được rỗng")

    for idx, row in enumerate(rows):
        ok, msg = validate_row_18_columns(row)
        if not ok:
            raise ValueError(f"Dòng {idx + 1} không hợp lệ: {msg}")

    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return os.path.abspath(output_file)


def create_sample_rows():
    return [
        [
            "run", "chạy", "I run every morning",
            "walk", "đi bộ", "She walks to school",
            "jump", "nhảy", "The kids jump high",
            "climb", "leo trèo", "Cats climb trees",
            "stand", "đứng", "Please stand up",
            "sit", "ngồi", "Sit down on the chair"
        ],
        [
            "eat", "ăn", "I eat breakfast",
            "drink", "uống", "Drink some water",
            "sleep", "ngủ", "The baby is sleeping",
            "wake up", "thức dậy", "I wake up at 6 a.m.",
            "laugh", "cười", "They laugh loudly",
            "cry", "khóc", "Do not cry, baby"
        ],
        [
            "dog", "con chó", "I have a dog",
            "cat", "con mèo", "The cat is cute",
            "bird", "con chim", "A bird is flying",
            "fish", "con cá", "Fish live in water",
            "duck", "con vịt", "The duck can swim",
            "rabbit", "con thỏ", "The rabbit jumps fast"
        ]
    ]


# =========================================================
# VIDEO ENGINE
# =========================================================
class VideoGenerator:
    def __init__(self, log_callback, progress_callback, done_callback):
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.done_callback = done_callback

        self.task_queue = Queue()
        self.stop_event = threading.Event()
        self.worker_thread = None
        self.total_tasks = 0
        self.finished_tasks = 0
        self.is_running = False

    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)

    def progress(self):
        if self.progress_callback:
            self.progress_callback()

    def done(self):
        if self.done_callback:
            self.done_callback()

    def make_voice(self, text, filename):
        """
        Dùng Windows Speech API tạo file WAV
        """
        safe_text = safe_ps_text(text)
        ps_cmd = f'''
Add-Type -AssemblyName System.Speech;
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer;
$speak.Rate = 0;
$speak.Volume = 100;
$speak.SetOutputToWaveFile("{filename}");
$speak.Speak("{safe_text}");
$speak.Dispose();
'''
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Lỗi không xác định khi tạo giọng đọc")

        if not os.path.exists(filename):
            raise RuntimeError("Không tạo được file âm thanh WAV")

    def get_audio_duration(self, audio_file):
        """
        Lấy thời lượng audio bằng ffprobe nếu có, fallback 4 giây
        """
        ffprobe_path = os.path.join(BASE_DIR, "ffprobe.exe")
        if not os.path.exists(ffprobe_path):
            return 4.0

        try:
            cmd = [
                ffprobe_path,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_file
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
            duration = float(result.stdout.strip())
            if duration <= 0:
                return 4.0
            return duration
        except Exception:
            return 4.0

    def render_segment(self, word, meaning, example, idx, seg_idx):
        """
        Tạo 1 segment video cho 1 từ
        """
        ensure_output_dir()

        audio_file = os.path.join(OUTPUT_DIR, f"temp_audio_{idx}_{seg_idx}.wav")
        video_file = os.path.join(OUTPUT_DIR, f"temp_segment_{idx}_{seg_idx}.mp4")

        speech_text = f"{word}. {meaning}. Example. {example}"
        self.make_voice(speech_text, audio_file)

        duration = self.get_audio_duration(audio_file)
        duration = max(duration + 0.5, 3.0)

        display_text = f"{word}\\n({meaning})\\n{example}"
        display_text = safe_ffmpeg_text(display_text)

        bg = random_bg()

        vf = (
            f"drawtext=fontfile='{FONT_PATH}':"
            f"text='{display_text}':"
            f"fontcolor=white:"
            f"fontsize=46:"
            f"line_spacing=18:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2"
        )

        cmd = [
            FFMPEG_PATH,
            "-y",
            "-f", "lavfi",
            "-i", f"color=c={bg}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:d={duration}",
            "-i", audio_file,
            "-vf", vf,
            "-shortest",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            video_file
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-500:] if result.stderr else "Lỗi render segment")

        return audio_file, video_file

    def concat_segments(self, segment_files, output_file, idx):
        list_file = os.path.join(OUTPUT_DIR, f"concat_list_{idx}.txt")

        with open(list_file, "w", encoding="utf-8") as f:
            for seg in segment_files:
                seg_path = os.path.abspath(seg).replace("\\", "/")
                f.write(f"file '{seg_path}'\n")

        cmd = [
            FFMPEG_PATH,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_file
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-500:] if result.stderr else "Lỗi ghép video")

        if os.path.exists(list_file):
            os.remove(list_file)

    def render_video_from_row(self, row_data, idx):
        ok, msg = validate_row_18_columns(row_data)
        if not ok:
            raise ValueError(msg)

        self.log(f"🎬 Đang render video {idx + 1}...")

        items = []
        for i in range(0, 18, 3):
            word = normalize_text(row_data[i])
            meaning = normalize_text(row_data[i + 1])
            example = normalize_text(row_data[i + 2])
            items.append((word, meaning, example))

        audio_files = []
        segment_files = []

        try:
            for seg_idx, (word, meaning, example) in enumerate(items, start=1):
                if self.stop_event.is_set():
                    self.log("⛔ Đã dừng theo yêu cầu")
                    return

                self.log(f"  🔊 Tạo giọng đọc từ {seg_idx}/6: {word}")
                audio_file, video_file = self.render_segment(word, meaning, example, idx, seg_idx)
                audio_files.append(audio_file)
                segment_files.append(video_file)

            final_output = os.path.join(OUTPUT_DIR, f"video_vocab_{idx + 1}.mp4")
            self.log(f"  🔗 Đang ghép video {idx + 1}...")
            self.concat_segments(segment_files, final_output, idx)

            self.log(f"✅ Hoàn thành: {final_output}")

        finally:
            for f in audio_files + segment_files:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception:
                    pass

    def worker(self):
        while not self.stop_event.is_set():
            try:
                item = self.task_queue.get(timeout=0.5)
            except Empty:
                if self.finished_tasks >= self.total_tasks:
                    break
                continue

            if item is None:
                self.task_queue.task_done()
                break

            row_data, idx = item

            try:
                self.render_video_from_row(row_data, idx)
            except Exception as e:
                self.log(f"❌ Lỗi video {idx + 1}: {e}")
            finally:
                self.finished_tasks += 1
                self.progress()
                self.task_queue.task_done()

        self.is_running = False
        self.done()

    def start(self, df):
        if self.is_running:
            raise RuntimeError("Đang có tiến trình render chạy")

        self.stop_event.clear()
        self.finished_tasks = 0
        self.total_tasks = len(df)
        self.is_running = True

        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
                self.task_queue.task_done()
            except Exception:
                break

        for idx, row in df.iterrows():
            self.task_queue.put((row.tolist(), idx))

        self.worker_thread = threading.Thread(target=self.worker, daemon=True)
        self.worker_thread.start()

    def stop(self):
        self.stop_event.set()
        self.task_queue.put(None)


# =========================================================
# GUI
# =========================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("980x760")

        self.df = None
        self.current_csv_path = DEFAULT_CSV_FILE

        self.generator = VideoGenerator(
            log_callback=self.safe_log,
            progress_callback=self.safe_progress,
            done_callback=self.on_render_done
        )

        self.build_ui()
        self.safe_log("🚀 Chương trình sẵn sàng")

    # ---------------- UI ----------------
    def build_ui(self):
        main = tk.Frame(self.root, bg="#f4f6f8")
        main.pack(fill="both", expand=True)

        header = tk.Label(
            main,
            text="🎓 ENGLISH VOCAB VIDEO FACTORY",
            font=("Segoe UI", 18, "bold"),
            bg="#f4f6f8",
            fg="#1f2937"
        )
        header.pack(pady=12)

        top_frame = tk.Frame(main, bg="#f4f6f8")
        top_frame.pack(fill="x", padx=12)

        left_frame = tk.LabelFrame(top_frame, text="📥 Quản lý dữ liệu CSV", font=("Segoe UI", 10, "bold"))
        left_frame.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        right_frame = tk.LabelFrame(top_frame, text="📝 Tạo 1 dòng dữ liệu 6 từ", font=("Segoe UI", 10, "bold"))
        right_frame.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        # Left controls
        btn_frame1 = tk.Frame(left_frame)
        btn_frame1.pack(fill="x", padx=10, pady=10)

        ttk.Button(btn_frame1, text="📄 Tạo CSV mẫu", command=self.create_demo_csv).pack(side="left", padx=4, pady=4)
        ttk.Button(btn_frame1, text="📂 Load CSV", command=self.load_csv).pack(side="left", padx=4, pady=4)
        ttk.Button(btn_frame1, text="✅ Kiểm tra CSV", command=self.validate_current_csv).pack(side="left", padx=4, pady=4)

        self.csv_path_var = tk.StringVar(value=self.current_csv_path)
        tk.Entry(left_frame, textvariable=self.csv_path_var, font=("Consolas", 10)).pack(fill="x", padx=10, pady=5)

        info_text = (
            "Mỗi dòng CSV phải có đúng 18 cột:\n"
            "Word1, Mean1, Example1, ..., Word6, Mean6, Example6"
        )
        tk.Label(left_frame, text=info_text, justify="left", fg="#374151").pack(anchor="w", padx=10, pady=5)

        # Right controls
        form_canvas = tk.Canvas(right_frame, height=280)
        form_canvas.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        form_scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=form_canvas.yview)
        form_scrollbar.pack(side="right", fill="y")

        form_canvas.configure(yscrollcommand=form_scrollbar.set)

        self.form_inner = tk.Frame(form_canvas)
        form_canvas.create_window((0, 0), window=self.form_inner, anchor="nw")

        self.form_inner.bind(
            "<Configure>",
            lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all"))
        )

        self.word_entries = []
        self.mean_entries = []
        self.example_entries = []

        for i in range(6):
            row = tk.LabelFrame(self.form_inner, text=f"Từ {i + 1}")
            row.pack(fill="x", padx=6, pady=4)

            tk.Label(row, text="Word", width=10).grid(row=0, column=0, padx=4, pady=4, sticky="w")
            tk.Label(row, text="Nghĩa", width=10).grid(row=1, column=0, padx=4, pady=4, sticky="w")
            tk.Label(row, text="Ví dụ", width=10).grid(row=2, column=0, padx=4, pady=4, sticky="w")

            word_e = tk.Entry(row, width=45)
            mean_e = tk.Entry(row, width=45)
            example_e = tk.Entry(row, width=45)

            word_e.grid(row=0, column=1, padx=4, pady=4)
            mean_e.grid(row=1, column=1, padx=4, pady=4)
            example_e.grid(row=2, column=1, padx=4, pady=4)

            self.word_entries.append(word_e)
            self.mean_entries.append(mean_e)
            self.example_entries.append(example_e)

        btn_frame2 = tk.Frame(right_frame)
        btn_frame2.pack(fill="x", padx=10, pady=8)

        ttk.Button(btn_frame2, text="✨ Điền dữ liệu mẫu", command=self.fill_form_sample).pack(side="left", padx=4)
        ttk.Button(btn_frame2, text="➕ Thêm thành 1 dòng vào CSV", command=self.add_form_row_to_csv).pack(side="left", padx=4)
        ttk.Button(btn_frame2, text="🧹 Xóa form", command=self.clear_form).pack(side="left", padx=4)

        # Render controls
        render_frame = tk.LabelFrame(main, text="🎬 Render video", font=("Segoe UI", 10, "bold"))
        render_frame.pack(fill="x", padx=12, pady=8)

        btn_frame3 = tk.Frame(render_frame)
        btn_frame3.pack(fill="x", padx=10, pady=10)

        self.start_btn = ttk.Button(btn_frame3, text="🚀 Bắt đầu render", command=self.start_render)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(btn_frame3, text="🛑 Dừng", command=self.stop_render)
        self.stop_btn.pack(side="left", padx=5)

        self.open_output_btn = ttk.Button(btn_frame3, text="📁 Mở thư mục output", command=self.open_output_folder)
        self.open_output_btn.pack(side="left", padx=5)

        self.progress = ttk.Progressbar(render_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=6)

        # Log
        log_frame = tk.LabelFrame(main, text="📋 Log", font=("Segoe UI", 10, "bold"))
        log_frame.pack(fill="both", expand=True, padx=12, pady=8)

        self.log_box = tk.Text(log_frame, height=16, font=("Consolas", 10), wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=8, pady=8)

    # ---------------- Safe UI updates ----------------
    def safe_log(self, msg):
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    def safe_progress(self):
        self.root.after(0, self._step_progress)

    def _step_progress(self):
        self.progress["value"] = min(self.progress["value"] + 1, self.progress["maximum"])

    def on_render_done(self):
        self.root.after(0, self._on_render_done_ui)

    def _on_render_done_ui(self):
        self.start_btn.config(state="normal")
        self.safe_log("🏁 Hoàn tất tiến trình render")

    # ---------------- CSV actions ----------------
    def create_demo_csv(self):
        try:
            path = create_csv_from_rows(create_sample_rows(), DEFAULT_CSV_FILE)
            self.current_csv_path = path
            self.csv_path_var.set(path)
            self.safe_log(f"✅ Đã tạo CSV mẫu: {path}")
            messagebox.showinfo("Thành công", f"Đã tạo file mẫu:\n{path}")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def load_csv(self):
        file_path = filedialog.askopenfilename(
            title="Chọn file CSV",
            filetypes=[("CSV files", "*.csv")]
        )
        if not file_path:
            return

        ok, msg, df = validate_csv_file(file_path)
        if not ok:
            messagebox.showerror("CSV lỗi", msg)
            return

        self.df = df
        self.current_csv_path = file_path
        self.csv_path_var.set(file_path)
        self.progress["maximum"] = len(df)
        self.progress["value"] = 0
        self.safe_log(f"📂 Đã load CSV: {file_path}")
        self.safe_log(f"✅ {msg}")

    def validate_current_csv(self):
        path = self.csv_path_var.get().strip()
        if not path:
            messagebox.showwarning("Thiếu file", "Chưa có đường dẫn CSV")
            return

        ok, msg, df = validate_csv_file(path)
        if ok:
            self.df = df
            self.progress["maximum"] = len(df)
            self.progress["value"] = 0
            messagebox.showinfo("Hợp lệ", msg)
            self.safe_log(f"✅ {msg}")
        else:
            messagebox.showerror("CSV lỗi", msg)
            self.safe_log(f"❌ {msg}")

    # ---------------- Form actions ----------------
    def fill_form_sample(self):
        sample = create_sample_rows()[0]

        for i in range(6):
            self.word_entries[i].delete(0, "end")
            self.mean_entries[i].delete(0, "end")
            self.example_entries[i].delete(0, "end")

            self.word_entries[i].insert(0, sample[i * 3])
            self.mean_entries[i].insert(0, sample[i * 3 + 1])
            self.example_entries[i].insert(0, sample[i * 3 + 2])

        self.safe_log("✨ Đã điền dữ liệu mẫu vào form")

    def clear_form(self):
        for i in range(6):
            self.word_entries[i].delete(0, "end")
            self.mean_entries[i].delete(0, "end")
            self.example_entries[i].delete(0, "end")

    def collect_form_row(self):
        row = []
        for i in range(6):
            word = normalize_text(self.word_entries[i].get())
            mean = normalize_text(self.mean_entries[i].get())
            example = normalize_text(self.example_entries[i].get())

            row.extend([word, mean, example])

        ok, msg = validate_row_18_columns(row)
        if not ok:
            raise ValueError(msg)

        return row

    def add_form_row_to_csv(self):
        try:
            row = self.collect_form_row()
        except Exception as e:
            messagebox.showerror("Dữ liệu không hợp lệ", str(e))
            return

        save_path = filedialog.asksaveasfilename(
            title="Lưu hoặc chọn file CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="data.csv"
        )

        if not save_path:
            return

        file_exists = os.path.exists(save_path) and os.path.getsize(save_path) > 0

        try:
            with open(save_path, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                if file_exists:
                    writer.writerow(row)
                else:
                    writer.writerow(row)

            self.current_csv_path = save_path
            self.csv_path_var.set(save_path)
            self.safe_log(f"➕ Đã thêm 1 dòng dữ liệu vào: {save_path}")
            messagebox.showinfo("Thành công", f"Đã thêm 1 dòng vào:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Lỗi ghi file", str(e))

    # ---------------- Render actions ----------------
    def start_render(self):
        ok_ffmpeg, msg_ffmpeg = check_ffmpeg()
        if not ok_ffmpeg:
            messagebox.showerror("Thiếu FFmpeg", msg_ffmpeg)
            return

        path = self.csv_path_var.get().strip()
        if not path:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng tạo hoặc load CSV trước")
            return

        ok, msg, df = validate_csv_file(path)
        if not ok:
            messagebox.showerror("CSV lỗi", msg)
            return

        self.df = df
        self.progress["maximum"] = len(df)
        self.progress["value"] = 0

        ensure_output_dir()

        try:
            self.generator.start(df)
            self.start_btn.config(state="disabled")
            self.safe_log(f"🚀 Bắt đầu render {len(df)} video...")
        except Exception as e:
            messagebox.showerror("Không thể start", str(e))

    def stop_render(self):
        self.generator.stop()
        self.start_btn.config(state="normal")
        self.safe_log("🛑 Đã gửi lệnh dừng")

    def open_output_folder(self):
        ensure_output_dir()
        try:
            os.startfile(OUTPUT_DIR)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không mở được thư mục output:\n{e}")


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
