# =========================================================
# POST MANAGER — Quản lý bài viết & đăng mạng xã hội
# =========================================================
import json
import os
import sys
import uuid
import threading
import datetime
import urllib.request
import urllib.parse
import urllib.error

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog


# ─────────────────────────── DATA FILE ───────────────────────────

def _get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR  = _get_base_dir()
DATA_FILE = os.path.join(BASE_DIR, "posts_data.json")

# ─────────────────────────── DATA MODEL ───────────────────────────
# posts_data.json schema:
# {
#   "topics": {
#     "<id>": {"name": "Animals", "created_at": "2026-04-22"}
#   },
#   "posts": {
#     "<id>": {
#       "topic_id": "<id>",
#       "title": "...",
#       "words": ["duck","fish",...],          # 6 từ tiếng Anh
#       "content": "...",                       # caption SEO
#       "video_path": "path/to/video.mp4",     # "" nếu chưa có
#       "platforms": {                          # trạng thái đăng
#         "facebook": {"status": "pending|posted|error", "post_id": "", "posted_at": ""},
#         "youtube":  {"status": "pending|posted|error", "post_id": "", "posted_at": ""}
#       },
#       "created_at": "2026-04-22 10:00"
#     }
#   }
# }

STATUS_PENDING = "pending"
STATUS_POSTED  = "posted"
STATUS_ERROR   = "error"
STATUS_SKIP    = "skip"   # bỏ qua nền tảng này


class PostDataStore:
    def __init__(self):
        self._data = {"topics": {}, "posts": {}}
        self.load()

    def load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                    self._data.setdefault("topics", {})
                    self._data.setdefault("posts", {})
            except Exception:
                pass

    def save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ── TOPICS ──
    def get_topics(self):
        return dict(self._data["topics"])

    def add_topic(self, name: str) -> str | None:
        name = name.strip()
        if not name:
            return None
        for t in self._data["topics"].values():
            if t["name"].lower() == name.lower():
                return None
        tid = str(uuid.uuid4())[:8]
        self._data["topics"][tid] = {
            "name": name,
            "created_at": _now_date()
        }
        self.save()
        return tid

    def rename_topic(self, tid: str, new_name: str) -> bool:
        new_name = new_name.strip()
        if tid not in self._data["topics"] or not new_name:
            return False
        self._data["topics"][tid]["name"] = new_name
        self.save()
        return True

    def delete_topic(self, tid: str) -> bool:
        if tid not in self._data["topics"]:
            return False
        del self._data["topics"][tid]
        # xóa cả bài viết thuộc topic này
        to_del = [pid for pid, p in self._data["posts"].items() if p["topic_id"] == tid]
        for pid in to_del:
            del self._data["posts"][pid]
        self.save()
        return True

    def get_topic_name(self, tid: str) -> str:
        return self._data["topics"].get(tid, {}).get("name", "?")

    # ── POSTS ──
    def get_posts(self, topic_id=None):
        posts = dict(self._data["posts"])
        if topic_id:
            posts = {pid: p for pid, p in posts.items() if p["topic_id"] == topic_id}
        return posts

    def add_post(self, topic_id: str, title: str, words: list,
                 content: str = "", video_path: str = "") -> str:
        pid = str(uuid.uuid4())[:8]
        self._data["posts"][pid] = {
            "topic_id": topic_id,
            "title": title,
            "words": words,
            "content": content,
            "video_path": video_path,
            "platforms": {
                "facebook": {"status": STATUS_PENDING, "post_id": "", "posted_at": ""},
                "youtube":  {"status": STATUS_PENDING, "post_id": "", "posted_at": ""},
            },
            "created_at": _now_dt()
        }
        self.save()
        return pid

    def update_post(self, pid: str, **kwargs):
        if pid not in self._data["posts"]:
            return False
        self._data["posts"][pid].update(kwargs)
        self.save()
        return True

    def set_platform_status(self, pid: str, platform: str, status: str,
                            post_id: str = "", posted_at: str = ""):
        if pid not in self._data["posts"]:
            return
        self._data["posts"][pid]["platforms"][platform] = {
            "status": status,
            "post_id": post_id,
            "posted_at": posted_at or _now_dt()
        }
        self.save()

    def delete_post(self, pid: str) -> bool:
        if pid not in self._data["posts"]:
            return False
        del self._data["posts"][pid]
        self.save()
        return True


def _now_date():
    return datetime.date.today().isoformat()

def _now_dt():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# ─────────────────────────── AI HELPERS ───────────────────────────

def _gemini_request(prompt: str, api_key: str, endpoint: str) -> str:
    """Gọi Gemini API, trả về text thô."""
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")
    url = f"{endpoint}?key={api_key}"
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def generate_words_for_topic(topic_name: str, api_key: str, endpoint: str,
                              count: int = 6) -> list[str]:
    """Sinh danh sách N từ tiếng Anh theo chủ đề bằng Gemini."""
    prompt = (
        f'Sinh đúng {count} từ tiếng Anh phổ biến thuộc chủ đề "{topic_name}" '
        f'phù hợp để dạy từ vựng cho người học tiếng Anh cơ bản.\n'
        f'Quy tắc:\n'
        f'- Chỉ trả về JSON array, không giải thích thêm\n'
        f'- Mỗi từ là 1 từ đơn hoặc cụm ngắn (tối đa 2 từ)\n'
        f'- Ví dụ đúng cho Animals: ["dog","cat","bird","fish","rabbit","elephant"]\n'
        f'Chủ đề: "{topic_name}"\n'
        f'Trả về JSON array {count} phần tử:'
    )
    text = _gemini_request(prompt, api_key, endpoint)
    text = text.replace("```json", "").replace("```", "").strip()
    words = json.loads(text)
    return [str(w).strip().lower() for w in words[:count]]


def generate_seo_content(topic_name: str, words: list[str],
                          platform: str, api_key: str, endpoint: str) -> str:
    """Sinh caption SEO cho Facebook hoặc YouTube."""
    word_list = ", ".join(words)
    if platform == "facebook":
        style = (
            "Viết caption Facebook thu hút, có emoji phù hợp, "
            "kêu gọi tương tác (like/comment/share), hashtag SEO cuối bài. "
            "Độ dài 150-250 từ tiếng Việt."
        )
    else:  # youtube
        style = (
            "Viết mô tả video YouTube chuẩn SEO: tiêu đề + mô tả chi tiết + timestamp giả định + hashtag. "
            "Độ dài 200-300 từ tiếng Việt."
        )
    prompt = (
        f'Bạn là chuyên gia content marketing cho kênh dạy tiếng Anh.\n'
        f'Chủ đề bài học: "{topic_name}"\n'
        f'6 từ vựng trong video: {word_list}\n'
        f'{style}\n'
        f'Chỉ trả về nội dung caption, không giải thích thêm.'
    )
    return _gemini_request(prompt, api_key, endpoint)


# ─────────────────────────── SOCIAL PUBLISHERS ───────────────────────────

def publish_to_facebook(video_path: str, caption: str,
                         page_id: str, access_token: str) -> dict:
    """
    Đăng video lên Facebook Page.
    Trả về {"success": bool, "post_id": str, "error": str}
    """
    try:
        # Bước 1: Upload video (resumable upload)
        init_url = f"https://graph-video.facebook.com/v19.0/{page_id}/videos"
        file_size = os.path.getsize(video_path)

        init_data = urllib.parse.urlencode({
            "upload_phase": "start",
            "file_size": file_size,
            "access_token": access_token,
        }).encode()
        req = urllib.request.Request(init_url, data=init_data, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            session = json.loads(r.read())
        video_id    = session["video_id"]
        upload_url  = session["upload_url"]

        # Bước 2: Transfer data
        with open(video_path, "rb") as vf:
            video_data = vf.read()
        transfer_data = urllib.parse.urlencode({
            "upload_phase": "transfer",
            "start_offset": 0,
            "video_file_chunk": video_data.hex(),
            "upload_session_id": session["upload_session_id"],
            "access_token": access_token,
        }).encode()
        req2 = urllib.request.Request(upload_url, data=transfer_data, method="POST")
        urllib.request.urlopen(req2, timeout=120)

        # Bước 3: Finish + đặt caption
        finish_data = urllib.parse.urlencode({
            "upload_phase": "finish",
            "upload_session_id": session["upload_session_id"],
            "description": caption,
            "access_token": access_token,
        }).encode()
        req3 = urllib.request.Request(init_url, data=finish_data, method="POST")
        with urllib.request.urlopen(req3, timeout=30) as r:
            result = json.loads(r.read())
        return {"success": True, "post_id": str(result.get("id", video_id)), "error": ""}

    except Exception as e:
        return {"success": False, "post_id": "", "error": str(e)}


def publish_to_youtube(video_path: str, title: str, description: str,
                        api_key: str, oauth_token: str) -> dict:
    """
    Đăng video lên YouTube (cần OAuth2 access token).
    Trả về {"success": bool, "post_id": str, "error": str}
    """
    try:
        import requests as req_lib

        # Upload metadata
        meta = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "categoryId": "27"  # Education
            },
            "status": {"privacyStatus": "public"}
        }
        upload_url = (
            "https://www.googleapis.com/upload/youtube/v3/videos"
            "?uploadType=multipart&part=snippet,status"
        )
        with open(video_path, "rb") as vf:
            resp = req_lib.post(
                upload_url,
                headers={"Authorization": f"Bearer {oauth_token}"},
                files={
                    "metadata": (None, json.dumps(meta), "application/json"),
                    "video":    (os.path.basename(video_path), vf, "video/mp4"),
                },
                timeout=300
            )
        if resp.status_code in (200, 201):
            data = resp.json()
            return {"success": True, "post_id": data.get("id", ""), "error": ""}
        return {"success": False, "post_id": "", "error": resp.text[:200]}
    except Exception as e:
        return {"success": False, "post_id": "", "error": str(e)}


# ─────────────────────────── UI ───────────────────────────

class PostManagerTab:
    """
    Widget chứa toàn bộ tab Quản lý bài viết.
    Dùng: PostManagerTab(parent_frame, app_ref)
    app_ref phải có: .engine, .gemini_key_var, .GEMINI_ENDPOINT, .safe_log, .ai_provider_var
    """

    def __init__(self, parent, app_ref):
        self.parent = parent
        self.app    = app_ref
        self.store  = PostDataStore()

        # Social credentials (đọc từ config nếu có)
        self.fb_page_id_var    = tk.StringVar()
        self.fb_token_var      = tk.StringVar()
        self.yt_oauth_var      = tk.StringVar()

        self._selected_topic_id = None
        self._selected_post_id  = None
        self._topic_id_map = {}   # listbox index → topic_id
        self._post_id_map  = {}   # listbox index → post_id

        self._build_ui()
        self.refresh_topics()

    # ═══════════════════════ LAYOUT ═══════════════════════

    def _build_ui(self):
        # Chia 3 cột: Topics | Posts list | Detail/Actions
        paned = tk.PanedWindow(self.parent, orient="horizontal", sashwidth=5,
                               bg="#e5e7eb")
        paned.pack(fill="both", expand=True, padx=6, pady=6)

        # ── Cột 1: Topics ──
        left = tk.Frame(paned, bg="#f0f4f8", width=200)
        paned.add(left, minsize=160)
        self._build_topic_panel(left)

        # ── Cột 2: Post list ──
        mid = tk.Frame(paned, bg="#f0f4f8", width=380)
        paned.add(mid, minsize=300)
        self._build_post_list_panel(mid)

        # ── Cột 3: Detail ──
        right = tk.Frame(paned, bg="#f0f4f8")
        paned.add(right, minsize=340)
        self._build_detail_panel(right)

    # ── TOPICS ──

    def _build_topic_panel(self, parent):
        tk.Label(parent, text="📂 Chủ đề", font=("Segoe UI", 11, "bold"),
                 bg="#f0f4f8").pack(anchor="w", padx=8, pady=(8, 2))

        self.topic_lb = tk.Listbox(parent, selectmode="single",
                                   exportselection=False, font=("Segoe UI", 10))
        self.topic_lb.pack(fill="both", expand=True, padx=6, pady=4)
        self.topic_lb.bind("<<ListboxSelect>>", self._on_topic_select)

        btn = tk.Frame(parent, bg="#f0f4f8")
        btn.pack(fill="x", padx=6, pady=(0, 6))
        tk.Button(btn, text="➕", width=3, command=self._add_topic).pack(side="left", padx=2)
        tk.Button(btn, text="✏", width=3, command=self._rename_topic).pack(side="left", padx=2)
        tk.Button(btn, text="❌", width=3, command=self._delete_topic).pack(side="left", padx=2)

    # ── POST LIST ──

    def _build_post_list_panel(self, parent):
        header = tk.Frame(parent, bg="#f0f4f8")
        header.pack(fill="x", padx=8, pady=(8, 2))
        tk.Label(header, text="📋 Bài viết", font=("Segoe UI", 11, "bold"),
                 bg="#f0f4f8").pack(side="left")
        tk.Button(header, text="➕ Tạo bài viết",
                  bg="#3b82f6", fg="white", font=("Segoe UI", 9, "bold"),
                  command=self._open_create_post_dialog).pack(side="right")

        # Treeview
        cols = ("title", "video", "fb", "yt", "created")
        self.post_tree = ttk.Treeview(parent, columns=cols, show="headings",
                                      selectmode="browse")
        for col, heading, width in [
            ("title",   "Tiêu đề",   180),
            ("video",   "Video",      60),
            ("fb",      "Facebook",   70),
            ("yt",      "YouTube",    70),
            ("created", "Ngày tạo",   90),
        ]:
            self.post_tree.heading(col, text=heading)
            self.post_tree.column(col, width=width, anchor="center")
        self.post_tree.column("title", anchor="w")

        scroll = ttk.Scrollbar(parent, orient="vertical",
                               command=self.post_tree.yview)
        self.post_tree.configure(yscrollcommand=scroll.set)
        self.post_tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=4)
        scroll.pack(side="right", fill="y", pady=4)

        self.post_tree.bind("<<TreeviewSelect>>", self._on_post_select)

        # Tag màu
        self.post_tree.tag_configure("posted",  foreground="#16a34a")
        self.post_tree.tag_configure("error",   foreground="#dc2626")
        self.post_tree.tag_configure("pending", foreground="#d97706")

    # ── DETAIL PANEL ──

    def _build_detail_panel(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True, padx=4, pady=4)

        # Tab info
        info_tab = tk.Frame(nb, bg="#f0f4f8")
        nb.add(info_tab, text="  📄 Chi tiết  ")
        self._build_info_tab(info_tab)

        # Tab actions
        act_tab = tk.Frame(nb, bg="#f0f4f8")
        nb.add(act_tab, text="  🚀 Đăng bài  ")
        self._build_publish_tab(act_tab)

        # Tab credentials
        cred_tab = tk.Frame(nb, bg="#f0f4f8")
        nb.add(cred_tab, text="  🔑 API Keys  ")
        self._build_cred_tab(cred_tab)

    def _build_info_tab(self, parent):
        pad = {"padx": 10, "pady": 3}

        tk.Label(parent, text="Tiêu đề:", bg="#f0f4f8",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", **pad)
        self.detail_title = tk.Entry(parent, font=("Segoe UI", 10))
        self.detail_title.pack(fill="x", **pad)

        tk.Label(parent, text="Từ vựng (cách nhau bằng dấu phẩy):", bg="#f0f4f8",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", **pad)
        self.detail_words = tk.Entry(parent, font=("Consolas", 10))
        self.detail_words.pack(fill="x", **pad)

        tk.Label(parent, text="Video:", bg="#f0f4f8",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", **pad)
        self.detail_video = tk.Entry(parent, font=("Consolas", 9), state="readonly")
        self.detail_video.pack(fill="x", **pad)

        tk.Label(parent, text="Caption / Nội dung bài viết:", bg="#f0f4f8",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", **pad)
        self.detail_content = scrolledtext.ScrolledText(parent, height=10,
                                                        font=("Segoe UI", 9),
                                                        wrap="word")
        self.detail_content.pack(fill="both", expand=True, **pad)

        btn = tk.Frame(parent, bg="#f0f4f8")
        btn.pack(fill="x", **pad)
        tk.Button(btn, text="💾 Lưu chỉnh sửa", bg="#3b82f6", fg="white",
                  command=self._save_post_edit).pack(side="left", padx=2)
        tk.Button(btn, text="❌ Xóa bài viết", bg="#ef4444", fg="white",
                  command=self._delete_post).pack(side="left", padx=2)

    def _build_publish_tab(self, parent):
        pad = {"padx": 12, "pady": 6}

        # Chọn nền tảng
        plat_frame = tk.LabelFrame(parent, text="Nền tảng đăng", bg="#f0f4f8")
        plat_frame.pack(fill="x", **pad)
        self.pub_fb_var = tk.BooleanVar(value=True)
        self.pub_yt_var = tk.BooleanVar(value=True)
        tk.Checkbutton(plat_frame, text="📘 Facebook", variable=self.pub_fb_var,
                       bg="#f0f4f8", font=("Segoe UI", 10)).pack(side="left", padx=10, pady=4)
        tk.Checkbutton(plat_frame, text="▶️ YouTube", variable=self.pub_yt_var,
                       bg="#f0f4f8", font=("Segoe UI", 10)).pack(side="left", padx=10, pady=4)

        # Nút đăng bài
        tk.Button(parent, text="🚀 Đăng bài viết này",
                  bg="#22c55e", fg="white", font=("Segoe UI", 11, "bold"),
                  command=self._publish_current_post).pack(fill="x", **pad)

        # Nút 1-click tạo + đăng
        tk.Frame(parent, height=1, bg="#d1d5db").pack(fill="x", padx=12)
        tk.Label(parent, text="⚡ 1-Click: Chọn chủ đề → Tự động sinh + đăng",
                 bg="#f0f4f8", fg="#6b7280", font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(8, 2))
        tk.Button(parent, text="⚡ 1-Click Tạo & Đăng bài mới",
                  bg="#8b5cf6", fg="white", font=("Segoe UI", 10, "bold"),
                  command=self._one_click_post).pack(fill="x", padx=12, pady=4)

        # Log
        tk.Label(parent, text="Log:", bg="#f0f4f8",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
        self.pub_log = scrolledtext.ScrolledText(parent, height=8, state="disabled",
                                                 font=("Consolas", 9))
        self.pub_log.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    def _build_cred_tab(self, parent):
        pad = {"padx": 12, "pady": 4}

        # Facebook
        fb_frame = tk.LabelFrame(parent, text="📘 Facebook Page", bg="#f0f4f8")
        fb_frame.pack(fill="x", **pad)
        tk.Label(fb_frame, text="Page ID:", bg="#f0f4f8").grid(
            row=0, column=0, sticky="w", padx=8, pady=4)
        tk.Entry(fb_frame, textvariable=self.fb_page_id_var,
                 width=38).grid(row=0, column=1, padx=6, pady=4)
        tk.Label(fb_frame, text="Access Token:", bg="#f0f4f8").grid(
            row=1, column=0, sticky="w", padx=8, pady=4)
        tk.Entry(fb_frame, textvariable=self.fb_token_var,
                 width=38, show="*").grid(row=1, column=1, padx=6, pady=4)
        tk.Label(fb_frame, text="💡 Lấy token tại: Meta for Developers → Graph API Explorer",
                 bg="#f0f4f8", fg="#6b7280", font=("Segoe UI", 8)).grid(
            row=2, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4))

        # YouTube
        yt_frame = tk.LabelFrame(parent, text="▶️ YouTube", bg="#f0f4f8")
        yt_frame.pack(fill="x", **pad)
        tk.Label(yt_frame, text="OAuth Token:", bg="#f0f4f8").grid(
            row=0, column=0, sticky="w", padx=8, pady=4)
        tk.Entry(yt_frame, textvariable=self.yt_oauth_var,
                 width=38, show="*").grid(row=0, column=1, padx=6, pady=4)
        tk.Label(yt_frame, text="💡 Token lấy qua Google OAuth2 Playground hoặc yt-dlp auth",
                 bg="#f0f4f8", fg="#6b7280", font=("Segoe UI", 8)).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4))

    # ═══════════════════════ TOPIC ACTIONS ═══════════════════════

    def refresh_topics(self):
        self.topic_lb.delete(0, tk.END)
        self._topic_id_map.clear()
        for i, (tid, t) in enumerate(self.store.get_topics().items()):
            self.topic_lb.insert(tk.END, f"  {t['name']}")
            self._topic_id_map[i] = tid

    def _on_topic_select(self, event=None):
        sel = self.topic_lb.curselection()
        if not sel:
            return
        self._selected_topic_id = self._topic_id_map.get(sel[0])
        self.refresh_posts()

    def _add_topic(self):
        name = simpledialog.askstring("Thêm chủ đề", "Tên chủ đề:", parent=self.parent)
        if not name:
            return
        tid = self.store.add_topic(name.strip())
        if tid:
            self.refresh_topics()
        else:
            messagebox.showwarning("Trùng", f"Chủ đề '{name}' đã tồn tại.")

    def _rename_topic(self):
        if not self._selected_topic_id:
            messagebox.showinfo("Chưa chọn", "Hãy chọn chủ đề cần đổi tên.")
            return
        old = self.store.get_topic_name(self._selected_topic_id)
        new = simpledialog.askstring("Đổi tên", f"Tên mới cho '{old}':",
                                     initialvalue=old, parent=self.parent)
        if new and self.store.rename_topic(self._selected_topic_id, new):
            self.refresh_topics()

    def _delete_topic(self):
        if not self._selected_topic_id:
            messagebox.showinfo("Chưa chọn", "Hãy chọn chủ đề cần xóa.")
            return
        name = self.store.get_topic_name(self._selected_topic_id)
        posts = self.store.get_posts(self._selected_topic_id)
        if not messagebox.askyesno("Xác nhận",
                f"Xóa chủ đề '{name}' và {len(posts)} bài viết liên quan?"):
            return
        self.store.delete_topic(self._selected_topic_id)
        self._selected_topic_id = None
        self.refresh_topics()
        self.refresh_posts()

    # ═══════════════════════ POST LIST ═══════════════════════

    def refresh_posts(self):
        for row in self.post_tree.get_children():
            self.post_tree.delete(row)
        self._post_id_map.clear()

        posts = self.store.get_posts(self._selected_topic_id)
        for i, (pid, p) in enumerate(sorted(posts.items(),
                                             key=lambda x: x[1]["created_at"],
                                             reverse=True)):
            fb_st = p["platforms"].get("facebook", {}).get("status", STATUS_PENDING)
            yt_st = p["platforms"].get("youtube",  {}).get("status", STATUS_PENDING)
            has_video = "✅" if p.get("video_path") and os.path.exists(p["video_path"]) else "❌"

            fb_icon = {"posted": "✅", "error": "❌", "pending": "⏳", "skip": "—"}.get(fb_st, "⏳")
            yt_icon = {"posted": "✅", "error": "❌", "pending": "⏳", "skip": "—"}.get(yt_st, "⏳")

            # tag màu row
            if fb_st == STATUS_POSTED and yt_st == STATUS_POSTED:
                tag = "posted"
            elif fb_st == STATUS_ERROR or yt_st == STATUS_ERROR:
                tag = "error"
            else:
                tag = "pending"

            self.post_tree.insert("", "end", iid=pid, tags=(tag,), values=(
                p.get("title", pid),
                has_video,
                fb_icon,
                yt_icon,
                p.get("created_at", "")[:10]
            ))
            self._post_id_map[i] = pid

    def _on_post_select(self, event=None):
        sel = self.post_tree.selection()
        if not sel:
            return
        pid = sel[0]
        self._selected_post_id = pid
        self._load_detail(pid)

    def _load_detail(self, pid: str):
        post = self.store.get_posts().get(pid)
        if not post:
            return
        self.detail_title.delete(0, tk.END)
        self.detail_title.insert(0, post.get("title", ""))

        self.detail_words.delete(0, tk.END)
        self.detail_words.insert(0, ", ".join(post.get("words", [])))

        self.detail_video.config(state="normal")
        self.detail_video.delete(0, tk.END)
        self.detail_video.insert(0, post.get("video_path", ""))
        self.detail_video.config(state="readonly")

        self.detail_content.delete("1.0", tk.END)
        self.detail_content.insert("1.0", post.get("content", ""))

    def _save_post_edit(self):
        if not self._selected_post_id:
            return
        self.store.update_post(self._selected_post_id,
                               title=self.detail_title.get().strip(),
                               words=[w.strip() for w in self.detail_words.get().split(",") if w.strip()],
                               content=self.detail_content.get("1.0", tk.END).strip())
        self.refresh_posts()
        self._pub_log("💾 Đã lưu chỉnh sửa.")

    def _delete_post(self):
        if not self._selected_post_id:
            return
        if messagebox.askyesno("Xác nhận", "Xóa bài viết này?"):
            self.store.delete_post(self._selected_post_id)
            self._selected_post_id = None
            self.refresh_posts()

    # ═══════════════════════ CREATE POST DIALOG ═══════════════════════

    def _open_create_post_dialog(self):
        if not self._selected_topic_id:
            messagebox.showinfo("Chưa chọn chủ đề", "Hãy chọn chủ đề trước khi tạo bài viết.")
            return
        CreatePostDialog(self.parent, self)

    # ═══════════════════════ PUBLISH ═══════════════════════

    def _publish_current_post(self):
        if not self._selected_post_id:
            messagebox.showinfo("Chưa chọn", "Hãy chọn bài viết cần đăng.")
            return
        post = self.store.get_posts().get(self._selected_post_id)
        if not post:
            return

        # Kiểm tra đã đăng chưa
        fb_done = post["platforms"]["facebook"]["status"] == STATUS_POSTED
        yt_done = post["platforms"]["youtube"]["status"]  == STATUS_POSTED
        if self.pub_fb_var.get() and fb_done:
            if not messagebox.askyesno("Cảnh báo", "Bài này đã đăng Facebook. Đăng lại?"):
                return
        if self.pub_yt_var.get() and yt_done:
            if not messagebox.askyesno("Cảnh báo", "Bài này đã đăng YouTube. Đăng lại?"):
                return

        threading.Thread(target=self._do_publish,
                         args=(self._selected_post_id,
                               self.pub_fb_var.get(),
                               self.pub_yt_var.get()),
                         daemon=True).start()

    def _do_publish(self, pid: str, do_fb: bool, do_yt: bool):
        post = self.store.get_posts().get(pid)
        if not post:
            return
        video = post.get("video_path", "")
        caption = post.get("content", "")
        title   = post.get("title", "Vocab Video")

        if not video or not os.path.exists(video):
            self._pub_log("❌ Chưa có video. Hãy render video trước.")
            return

        if do_fb:
            page_id = self.fb_page_id_var.get().strip()
            token   = self.fb_token_var.get().strip()
            if not page_id or not token:
                self._pub_log("❌ Facebook: Chưa nhập Page ID / Access Token.")
                self.store.set_platform_status(pid, "facebook", STATUS_ERROR,
                                               posted_at="", post_id="")
            else:
                self._pub_log("📘 Đang đăng lên Facebook...")
                result = publish_to_facebook(video, caption, page_id, token)
                if result["success"]:
                    self.store.set_platform_status(pid, "facebook", STATUS_POSTED,
                                                   post_id=result["post_id"])
                    self._pub_log(f"✅ Facebook OK! Post ID: {result['post_id']}")
                else:
                    self.store.set_platform_status(pid, "facebook", STATUS_ERROR)
                    self._pub_log(f"❌ Facebook lỗi: {result['error']}")

        if do_yt:
            yt_token = self.yt_oauth_var.get().strip()
            if not yt_token:
                self._pub_log("❌ YouTube: Chưa nhập OAuth Token.")
                self.store.set_platform_status(pid, "youtube", STATUS_ERROR)
            else:
                self._pub_log("▶️ Đang đăng lên YouTube...")
                result = publish_to_youtube(video, title, caption, "", yt_token)
                if result["success"]:
                    self.store.set_platform_status(pid, "youtube", STATUS_POSTED,
                                                   post_id=result["post_id"])
                    self._pub_log(f"✅ YouTube OK! Video ID: {result['post_id']}")
                else:
                    self.store.set_platform_status(pid, "youtube", STATUS_ERROR)
                    self._pub_log(f"❌ YouTube lỗi: {result['error']}")

        self.parent.after(0, self.refresh_posts)

    def _one_click_post(self):
        """Chọn chủ đề → sinh từ + content + video → đăng."""
        if not self._selected_topic_id:
            messagebox.showinfo("Chưa chọn chủ đề", "Hãy chọn chủ đề trước.")
            return
        do_fb = self.pub_fb_var.get()
        do_yt  = self.pub_yt_var.get()
        if not do_fb and not do_yt:
            messagebox.showinfo("Chưa chọn nền tảng",
                                "Hãy tích chọn ít nhất 1 nền tảng (Facebook/YouTube).")
            return
        threading.Thread(target=self._do_one_click,
                         args=(self._selected_topic_id, do_fb, do_yt),
                         daemon=True).start()

    def _do_one_click(self, topic_id: str, do_fb: bool, do_yt: bool):
        topic_name = self.store.get_topic_name(topic_id)
        gk = self._gemini_key()
        ep = self._gemini_endpoint()

        self._pub_log(f"⚡ Bắt đầu 1-Click cho chủ đề: {topic_name}")

        # 1. Sinh 6 từ
        self._pub_log("🔤 Đang sinh 6 từ vựng...")
        try:
            words = generate_words_for_topic(topic_name, gk, ep)
            self._pub_log(f"   Từ: {', '.join(words)}")
        except Exception as e:
            self._pub_log(f"❌ Sinh từ thất bại: {e}")
            return

        # 2. Sinh caption
        self._pub_log("✍️ Đang sinh caption SEO...")
        platform_for_content = "facebook" if do_fb else "youtube"
        try:
            content = generate_seo_content(topic_name, words,
                                           platform_for_content, gk, ep)
        except Exception as e:
            content = f"Học từ vựng tiếng Anh chủ đề {topic_name}: {', '.join(words)}"
            self._pub_log(f"⚠️ Sinh caption fallback: {e}")

        title = f"[{topic_name}] {', '.join(words[:3])}..."

        # 3. Tạo bài viết trong store
        pid = self.store.add_post(topic_id, title, words, content)
        self._pub_log(f"✅ Đã tạo bài viết ID: {pid}")
        self.parent.after(0, self.refresh_posts)

        # 4. Render video — gọi qua VideoEngine của app chính
        self._pub_log("🎬 Đang render video...")
        video_path = self._render_video_for_post(pid, words, topic_name=topic_name)
        if video_path:
            self.store.update_post(pid, video_path=video_path)
            self._pub_log(f"✅ Video: {video_path}")
        else:
            self._pub_log("⚠️ Render video thất bại. Tiếp tục đăng bài không có video.")

        # 5. Đăng
        self._do_publish(pid, do_fb, do_yt)

    def _render_video_for_post(self, pid: str, words: list,
                                topic_name: str = "") -> str:
        """Render 1 video từ 6 từ và trả về path file output."""
        try:
            from main_pro_plus_v4 import ai_lookup_word, AI_PROVIDER, GEMINI_API_KEY, OUTPUT_DIR

            row = []
            for w in words:
                meaning, example, _ = ai_lookup_word(
                    w, provider=AI_PROVIDER, gemini_key=GEMINI_API_KEY)
                row.extend([w, meaning, example])

            # Đảm bảo đúng 18 phần tử (6 từ × 3)
            while len(row) < 18:
                row.extend(["", "", ""])
            row = row[:18]

            done_event = threading.Event()
            result_path = [None]

            def on_done():
                # Tìm file video mới nhất trong OUTPUT_DIR
                import glob
                files = sorted(
                    glob.glob(os.path.join(OUTPUT_DIR, "vocab_video_*.mp4")),
                    key=os.path.getmtime, reverse=True
                )
                if files:
                    result_path[0] = files[0]
                done_event.set()

            engine = self.app.engine
            # Truyền chủ đề để video background tìm kiếm phù hợp hơn
            old_topic       = engine.current_topic
            old_done        = engine.done_fn
            engine.current_topic = topic_name
            engine.done_fn  = on_done
            engine.start([row])
            done_event.wait(timeout=300)
            engine.done_fn       = old_done
            engine.current_topic = old_topic
            return result_path[0]
        except Exception as e:
            self._pub_log(f"❌ Render lỗi: {e}")
            return None

    # ═══════════════════════ HELPERS ═══════════════════════

    def _gemini_key(self) -> str:
        try:
            return self.app.gemini_key_var.get().strip()
        except Exception:
            from main_pro_plus_v4 import GEMINI_API_KEY
            return GEMINI_API_KEY

    def _gemini_endpoint(self) -> str:
        try:
            from main_pro_plus_v4 import GEMINI_ENDPOINT
            return GEMINI_ENDPOINT
        except Exception:
            return "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def _pub_log(self, msg: str):
        def _do():
            self.pub_log.config(state="normal")
            self.pub_log.insert("end", f"{_now_dt().split()[1]}  {msg}\n")
            self.pub_log.see("end")
            self.pub_log.config(state="disabled")
        try:
            self.parent.after(0, _do)
        except Exception:
            pass


# ─────────────────────────── CREATE POST DIALOG ───────────────────────────

class CreatePostDialog(tk.Toplevel):
    """Dialog tạo bài viết mới — từng bước hoặc tự động."""

    def __init__(self, parent, manager: PostManagerTab):
        super().__init__(parent)
        self.manager = manager
        self.title("✏️ Tạo bài viết mới")
        self.geometry("640x620")
        self.resizable(False, False)
        self.grab_set()

        self._words = []
        self._pid   = None
        self._build()

    def _build(self):
        bg = "#f8fafc"
        self.configure(bg=bg)

        topic_name = self.manager.store.get_topic_name(
            self.manager._selected_topic_id)
        tk.Label(self, text=f"Chủ đề: {topic_name}",
                 font=("Segoe UI", 12, "bold"), bg=bg).pack(pady=(14, 4))

        # ── Bước 1: từ vựng ──
        s1 = tk.LabelFrame(self, text="Bước 1 — Từ vựng (6 từ)", bg=bg)
        s1.pack(fill="x", padx=16, pady=6)
        self.words_entry = tk.Entry(s1, font=("Consolas", 10))
        self.words_entry.pack(fill="x", padx=8, pady=6)
        tk.Label(s1, text="Nhập tay (cách nhau bằng dấu phẩy) hoặc:",
                 bg=bg, fg="#6b7280", font=("Segoe UI", 8)).pack(anchor="w", padx=8)
        tk.Button(s1, text="🤖 AI sinh từ tự động",
                  command=self._ai_gen_words).pack(anchor="w", padx=8, pady=(2, 8))

        # ── Bước 2: caption ──
        s2 = tk.LabelFrame(self, text="Bước 2 — Caption / Nội dung bài viết", bg=bg)
        s2.pack(fill="both", expand=True, padx=16, pady=6)

        plat_row = tk.Frame(s2, bg=bg)
        plat_row.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(plat_row, text="Nền tảng:", bg=bg).pack(side="left")
        self.cap_plat = tk.StringVar(value="facebook")
        for label, val in [("Facebook", "facebook"), ("YouTube", "youtube")]:
            tk.Radiobutton(plat_row, text=label, variable=self.cap_plat,
                           value=val, bg=bg).pack(side="left", padx=6)

        self.content_box = scrolledtext.ScrolledText(s2, height=8,
                                                     font=("Segoe UI", 9), wrap="word")
        self.content_box.pack(fill="both", expand=True, padx=8, pady=4)
        tk.Button(s2, text="🤖 AI sinh caption tự động",
                  command=self._ai_gen_caption).pack(anchor="w", padx=8, pady=(0, 8))

        # ── Bước 3: render & đăng ──
        s3 = tk.LabelFrame(self, text="Bước 3 — Lưu / Render / Đăng", bg=bg)
        s3.pack(fill="x", padx=16, pady=6)
        btn_row = tk.Frame(s3, bg=bg)
        btn_row.pack(pady=8)
        tk.Button(btn_row, text="💾 Lưu bài viết",
                  bg="#3b82f6", fg="white",
                  command=self._save_only).pack(side="left", padx=6)
        tk.Button(btn_row, text="🎬 Lưu + Render video",
                  bg="#f59e0b", fg="white",
                  command=self._save_and_render).pack(side="left", padx=6)
        tk.Button(btn_row, text="🚀 Lưu + Render + Đăng",
                  bg="#22c55e", fg="white",
                  command=self._save_render_publish).pack(side="left", padx=6)

        self.status_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.status_var, fg="#6b7280",
                 bg=bg, font=("Segoe UI", 9)).pack(pady=(0, 8))

    def _get_words(self) -> list:
        raw = self.words_entry.get().strip()
        return [w.strip().lower() for w in raw.split(",") if w.strip()]

    def _ai_gen_words(self):
        self.status_var.set("⏳ Đang sinh từ vựng...")
        def run():
            try:
                topic = self.manager.store.get_topic_name(
                    self.manager._selected_topic_id)
                words = generate_words_for_topic(
                    topic,
                    self.manager._gemini_key(),
                    self.manager._gemini_endpoint()
                )
                self.words_entry.delete(0, tk.END)
                self.words_entry.insert(0, ", ".join(words))
                self.status_var.set(f"✅ Đã sinh {len(words)} từ")
            except Exception as e:
                self.status_var.set(f"❌ {e}")
        threading.Thread(target=run, daemon=True).start()

    def _ai_gen_caption(self):
        words = self._get_words()
        if not words:
            messagebox.showwarning("Thiếu từ", "Hãy nhập hoặc sinh từ vựng trước.")
            return
        self.status_var.set("⏳ Đang sinh caption...")
        def run():
            try:
                topic = self.manager.store.get_topic_name(
                    self.manager._selected_topic_id)
                content = generate_seo_content(
                    topic, words, self.cap_plat.get(),
                    self.manager._gemini_key(),
                    self.manager._gemini_endpoint()
                )
                self.content_box.delete("1.0", tk.END)
                self.content_box.insert("1.0", content)
                self.status_var.set("✅ Đã sinh caption")
            except Exception as e:
                self.status_var.set(f"❌ {e}")
        threading.Thread(target=run, daemon=True).start()

    def _make_post(self) -> str | None:
        words = self._get_words()
        if len(words) < 1:
            messagebox.showwarning("Thiếu từ", "Hãy nhập ít nhất 1 từ.")
            return None
        content = self.content_box.get("1.0", tk.END).strip()
        topic_name = self.manager.store.get_topic_name(
            self.manager._selected_topic_id)
        title = f"[{topic_name}] {', '.join(words[:3])}..."
        pid = self.manager.store.add_post(
            self.manager._selected_topic_id, title, words, content)
        self.manager.refresh_posts()
        return pid

    def _save_only(self):
        pid = self._make_post()
        if pid:
            self.status_var.set(f"✅ Đã lưu bài viết ID: {pid}")
            self.after(1200, self.destroy)

    def _save_and_render(self):
        pid = self._make_post()
        if not pid:
            return
        self.status_var.set("🎬 Đang render video...")
        def run():
            post = self.manager.store.get_posts().get(pid, {})
            words = post.get("words", [])
            topic_name = self.manager.store.get_topic_name(post.get("topic_id", ""))
            vp = self.manager._render_video_for_post(pid, words, topic_name=topic_name)
            if vp:
                self.manager.store.update_post(pid, video_path=vp)
                self.manager.refresh_posts()
                self.status_var.set(f"✅ Render xong: {os.path.basename(vp)}")
            else:
                self.status_var.set("❌ Render thất bại")
        threading.Thread(target=run, daemon=True).start()

    def _save_render_publish(self):
        pid = self._make_post()
        if not pid:
            return
        self.status_var.set("🎬 Đang render video...")
        def run():
            post = self.manager.store.get_posts().get(pid, {})
            words = post.get("words", [])
            topic_name = self.manager.store.get_topic_name(post.get("topic_id", ""))
            vp = self.manager._render_video_for_post(pid, words, topic_name=topic_name)
            if vp:
                self.manager.store.update_post(pid, video_path=vp)
                self.manager.refresh_posts()
                self.status_var.set("🚀 Đang đăng bài...")
                self.manager._do_publish(pid,
                                         self.manager.pub_fb_var.get(),
                                         self.manager.pub_yt_var.get())
                self.status_var.set("✅ Hoàn tất!")
            else:
                self.status_var.set("❌ Render thất bại, không đăng bài")
        threading.Thread(target=run, daemon=True).start()
