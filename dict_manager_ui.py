import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from dictionary_lib import get_dict


class DictManagerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📚 Dictionary Manager")
        self.root.geometry("900x620")
        self.root.resizable(True, True)

        self.dict = get_dict()

        # State
        self.selected_group = None
        self.selected_word_key = None   # key chính xác trong dict (lowercase)
        self._search_mode = False       # True khi đang hiển thị kết quả search

        self._build_ui()
        self.refresh_groups()

    # ─────────────────────────── UI BUILD ───────────────────────────

    def _build_ui(self):
        main = tk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=6, pady=6)

        # ── LEFT: Groups ──
        left = tk.LabelFrame(main, text="📂 Nhóm", width=200)
        left.pack(side="left", fill="y", padx=(0, 4))
        left.pack_propagate(False)

        self.group_list = tk.Listbox(left, selectmode="single", exportselection=False)
        self.group_list.pack(fill="both", expand=True, padx=4, pady=4)
        self.group_list.bind("<<ListboxSelect>>", self.on_group_select)

        btn_frame_left = tk.Frame(left)
        btn_frame_left.pack(fill="x", padx=4, pady=(0, 4))
        tk.Button(btn_frame_left, text="➕ Thêm nhóm", command=self.add_group).pack(fill="x")
        tk.Button(btn_frame_left, text="✏ Đổi tên", command=self.rename_group).pack(fill="x")
        tk.Button(btn_frame_left, text="❌ Xóa nhóm", command=self.delete_group).pack(fill="x")

        # ── CENTER: Words ──
        center = tk.LabelFrame(main, text="📋 Từ vựng")
        center.pack(side="left", fill="both", expand=True, padx=(0, 4))

        search_frame = tk.Frame(center)
        search_frame.pack(fill="x", padx=4, pady=4)
        tk.Label(search_frame, text="🔍").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search_changed())
        tk.Entry(search_frame, textvariable=self.search_var).pack(side="left", fill="x", expand=True)
        tk.Button(search_frame, text="✕", width=2, command=self.clear_search).pack(side="left")

        self.word_list = tk.Listbox(center, selectmode="single", exportselection=False)
        self.word_list.pack(fill="both", expand=True, padx=4)
        self.word_list.bind("<<ListboxSelect>>", self.on_word_select)

        self._word_list_data = []  # danh sách (word_key, group_name) tương ứng với từng dòng

        # ── RIGHT: Form ──
        right = tk.LabelFrame(main, text="✏ Chỉnh sửa", width=280)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        pad = {"padx": 8, "pady": 2}

        tk.Label(right, text="Từ (Word):").pack(anchor="w", **pad)
        self.word_entry = tk.Entry(right)
        self.word_entry.pack(fill="x", **pad)

        tk.Label(right, text="Nghĩa (Meaning):").pack(anchor="w", **pad)
        self.mean_entry = tk.Entry(right)
        self.mean_entry.pack(fill="x", **pad)

        tk.Label(right, text="Ví dụ (Example):").pack(anchor="w", **pad)
        self.ex_entry = tk.Entry(right)
        self.ex_entry.pack(fill="x", **pad)

        tk.Frame(right, height=8).pack()

        tk.Button(right, text="➕ Thêm từ", command=self.add_word,
                  bg="#22c55e", fg="white").pack(fill="x", **pad)
        tk.Button(right, text="✏ Cập nhật", command=self.update_word,
                  bg="#3b82f6", fg="white").pack(fill="x", **pad)
        tk.Button(right, text="❌ Xóa từ", command=self.delete_word,
                  bg="#ef4444", fg="white").pack(fill="x", **pad)
        tk.Button(right, text="🗑 Xóa form", command=self.clear_form).pack(fill="x", **pad)

        # Status bar
        self.status_var = tk.StringVar(value="Sẵn sàng")
        tk.Label(self.root, textvariable=self.status_var, anchor="w",
                 relief="sunken", fg="#6b7280").pack(fill="x", side="bottom")

    # ─────────────────────────── GROUPS ───────────────────────────

    def refresh_groups(self):
        self.group_list.delete(0, tk.END)
        for g in self.dict.get_groups():
            self.group_list.insert(tk.END, g)
        self._update_status()

    def on_group_select(self, event=None):
        sel = self.group_list.curselection()
        if not sel:
            return
        self.selected_group = self.group_list.get(sel[0])
        self.clear_search()
        self.refresh_words()

    def add_group(self):
        name = simpledialog.askstring("Thêm nhóm", "Tên nhóm mới:", parent=self.root)
        if not name:
            return
        name = name.strip().upper()
        if self.dict.add_group(name):
            self.refresh_groups()
            self._select_group(name)
            self.set_status(f"✅ Đã thêm nhóm '{name}'")
        else:
            messagebox.showwarning("Trùng tên", f"Nhóm '{name}' đã tồn tại.")

    def rename_group(self):
        if not self.selected_group:
            messagebox.showinfo("Chưa chọn", "Hãy chọn nhóm cần đổi tên.")
            return
        new_name = simpledialog.askstring(
            "Đổi tên nhóm",
            f"Tên mới cho '{self.selected_group}':",
            initialvalue=self.selected_group,
            parent=self.root
        )
        if not new_name:
            return
        new_name = new_name.strip().upper()
        if self.dict.rename_group(self.selected_group, new_name):
            old = self.selected_group
            self.selected_group = new_name
            self.refresh_groups()
            self._select_group(new_name)
            self.set_status(f"✅ Đã đổi tên '{old}' → '{new_name}'")
        else:
            messagebox.showwarning("Lỗi", f"Không thể đổi tên. Tên '{new_name}' có thể đã tồn tại.")

    def delete_group(self):
        if not self.selected_group:
            messagebox.showinfo("Chưa chọn", "Hãy chọn nhóm cần xóa.")
            return
        count = len(self.dict.get_words_in_group(self.selected_group))
        if not messagebox.askyesno(
            "Xác nhận xóa",
            f"Xóa nhóm '{self.selected_group}' ({count} từ)?\nHành động này không thể hoàn tác."
        ):
            return
        self.dict.delete_group(self.selected_group)
        self.selected_group = None
        self.selected_word_key = None
        self.refresh_groups()
        self._clear_word_list()
        self.clear_form()
        self.set_status("🗑 Đã xóa nhóm")

    def _select_group(self, name):
        """Chọn đúng nhóm trong listbox theo tên."""
        groups = self.group_list.get(0, tk.END)
        if name in groups:
            idx = list(groups).index(name)
            self.group_list.selection_clear(0, tk.END)
            self.group_list.selection_set(idx)
            self.group_list.see(idx)

    # ─────────────────────────── WORDS ───────────────────────────

    def refresh_words(self):
        self._search_mode = False
        self._clear_word_list()
        if not self.selected_group:
            return
        words = self.dict.get_words_in_group(self.selected_group)
        for word_key in sorted(words.keys()):
            self.word_list.insert(tk.END, word_key)
            self._word_list_data.append((word_key, self.selected_group))
        self._update_status()

    def on_word_select(self, event=None):
        sel = self.word_list.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._word_list_data):
            return

        word_key, group_name = self._word_list_data[idx]
        data = self.dict.get_words_in_group(group_name).get(word_key)
        if data is None:
            return

        self.selected_word_key = word_key

        self.word_entry.delete(0, tk.END)
        self.word_entry.insert(0, word_key)

        self.mean_entry.delete(0, tk.END)
        self.mean_entry.insert(0, data.get("meaning", ""))

        self.ex_entry.delete(0, tk.END)
        self.ex_entry.insert(0, data.get("example", ""))

        if self._search_mode:
            self.selected_group = group_name
            self._select_group(group_name)

    def add_word(self):
        if not self.selected_group:
            messagebox.showinfo("Chưa chọn nhóm", "Hãy chọn nhóm trước khi thêm từ.")
            return
        word = self.word_entry.get().strip()
        meaning = self.mean_entry.get().strip()
        example = self.ex_entry.get().strip()
        if not word:
            messagebox.showwarning("Thiếu từ", "Hãy nhập từ cần thêm.")
            return
        if self.dict.add_word(self.selected_group, word, meaning, example):
            self.refresh_words()
            self.set_status(f"✅ Đã thêm '{word}' vào nhóm '{self.selected_group}'")
        else:
            messagebox.showwarning("Trùng từ", f"Từ '{word}' đã tồn tại trong nhóm này.")

    def update_word(self):
        if not self.selected_group or not self.selected_word_key:
            messagebox.showinfo("Chưa chọn", "Hãy chọn từ cần cập nhật.")
            return
        word = self.word_entry.get().strip()
        meaning = self.mean_entry.get().strip()
        example = self.ex_entry.get().strip()
        if self.dict.update_word(self.selected_group, self.selected_word_key, meaning, example):
            self.refresh_words()
            self.set_status(f"✅ Đã cập nhật '{self.selected_word_key}'")
        else:
            messagebox.showerror("Lỗi", "Không thể cập nhật từ.")

    def delete_word(self):
        if not self.selected_group or not self.selected_word_key:
            messagebox.showinfo("Chưa chọn", "Hãy chọn từ cần xóa.")
            return
        if not messagebox.askyesno("Xác nhận", f"Xóa từ '{self.selected_word_key}'?"):
            return
        if self.dict.delete_word(self.selected_group, self.selected_word_key):
            self.selected_word_key = None
            self.refresh_words()
            self.clear_form()
            self.set_status("🗑 Đã xóa từ")
        else:
            messagebox.showerror("Lỗi", "Không thể xóa từ.")

    # ─────────────────────────── SEARCH ───────────────────────────

    def _on_search_changed(self):
        query = self.search_var.get().strip()
        if query:
            self._do_search(query)
        else:
            # Quay về hiển thị nhóm đang chọn
            self.refresh_words()

    def _do_search(self, query: str):
        self._search_mode = True
        self._clear_word_list()
        results = self.dict.search(query)
        for word, meaning, example, group_name in results:
            self.word_list.insert(tk.END, f"{word}  [{group_name}]  — {meaning}")
            self._word_list_data.append((word, group_name))
        self.set_status(f"🔍 Tìm thấy {len(results)} kết quả cho '{query}'")

    def clear_search(self):
        self.search_var.set("")
        # trace_add sẽ tự gọi _on_search_changed → refresh_words

    # ─────────────────────────── HELPERS ───────────────────────────

    def _clear_word_list(self):
        self.word_list.delete(0, tk.END)
        self._word_list_data = []

    def clear_form(self):
        self.word_entry.delete(0, tk.END)
        self.mean_entry.delete(0, tk.END)
        self.ex_entry.delete(0, tk.END)
        self.selected_word_key = None

    def set_status(self, msg: str):
        self.status_var.set(msg)

    def _update_status(self):
        stats = self.dict.get_stats()
        groups = self.selected_group or "—"
        count = len(self.dict.get_words_in_group(self.selected_group)) if self.selected_group else 0
        self.set_status(
            f"Tổng: {stats['total_groups']} nhóm | {stats['total_words']} từ"
            + (f"  |  Nhóm '{groups}': {count} từ" if self.selected_group else "")
        )


# ─────────────────────────── ENTRY POINT ───────────────────────────

def open_dict_manager_window(parent=None):
    """Mở DictManagerUI trong Toplevel (dùng từ app chính)."""
    win = tk.Toplevel(parent)
    DictManagerUI(win)


def main():
    root = tk.Tk()
    DictManagerUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
