import tkinter as tk
from tkinter import ttk, messagebox
from dictionary_lib import get_dict

class DictManagerUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📚 Dictionary Manager")
        self.root.geometry("900x600")

        self.dict = get_dict()

        self.selected_group = None
        self.selected_word = None

        self._build_ui()
        self.refresh_groups()

    # ================= UI =================
    def _build_ui(self):
        main = tk.Frame(self.root)
        main.pack(fill="both", expand=True)

        # LEFT - GROUPS
        left = tk.Frame(main, width=200)
        left.pack(side="left", fill="y")

        tk.Label(left, text="📂 Groups").pack()

        self.group_list = tk.Listbox(left)
        self.group_list.pack(fill="y", expand=True)
        self.group_list.bind("<<ListboxSelect>>", self.on_group_select)

        tk.Button(left, text="➕ Add", command=self.add_group).pack(fill="x")
        tk.Button(left, text="❌ Delete", command=self.delete_group).pack(fill="x")

        # CENTER - WORDS
        center = tk.Frame(main)
        center.pack(side="left", fill="both", expand=True)

        tk.Label(center, text="🔍 Search").pack()
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.search_words())
        tk.Entry(center, textvariable=self.search_var).pack(fill="x")

        self.word_list = tk.Listbox(center)
        self.word_list.pack(fill="both", expand=True)
        self.word_list.bind("<<ListboxSelect>>", self.on_word_select)

        # RIGHT - FORM
        right = tk.Frame(main, width=300)
        right.pack(side="right", fill="y")

        tk.Label(right, text="Word").pack()
        self.word_entry = tk.Entry(right)
        self.word_entry.pack(fill="x")

        tk.Label(right, text="Meaning").pack()
        self.mean_entry = tk.Entry(right)
        self.mean_entry.pack(fill="x")

        tk.Label(right, text="Example").pack()
        self.ex_entry = tk.Entry(right)
        self.ex_entry.pack(fill="x")

        tk.Button(right, text="➕ Add", command=self.add_word).pack(fill="x")
        tk.Button(right, text="✏ Update", command=self.update_word).pack(fill="x")
        tk.Button(right, text="❌ Delete", command=self.delete_word).pack(fill="x")

    # ================= GROUP =================
    def refresh_groups(self):
        self.group_list.delete(0, tk.END)
        for g in self.dict.get_groups():
            self.group_list.insert(tk.END, g)

    def on_group_select(self, event):
        sel = self.group_list.curselection()
        if not sel:
            return
        self.selected_group = self.group_list.get(sel[0])
        self.refresh_words()

    def add_group(self):
        name = self.word_entry.get()
        if self.dict.add_group(name):
            self.refresh_groups()

    def delete_group(self):
        if self.selected_group:
            self.dict.delete_group(self.selected_group)
            self.refresh_groups()
            self.word_list.delete(0, tk.END)

    # ================= WORD =================
    def refresh_words(self):
        self.word_list.delete(0, tk.END)
        words = self.dict.get_words_in_group(self.selected_group)
        for w in words:
            self.word_list.insert(tk.END, w)

    def on_word_select(self, event):
        sel = self.word_list.curselection()
        if not sel:
            return
        word = self.word_list.get(sel[0])
        data = self.dict.get_words_in_group(self.selected_group)[word]

        self.word_entry.delete(0, tk.END)
        self.word_entry.insert(0, word)

        self.mean_entry.delete(0, tk.END)
        self.mean_entry.insert(0, data["meaning"])

        self.ex_entry.delete(0, tk.END)
        self.ex_entry.insert(0, data["example"])

    def add_word(self):
        if not self.selected_group:
            return
        self.dict.add_word(
            self.selected_group,
            self.word_entry.get(),
            self.mean_entry.get(),
            self.ex_entry.get()
        )
        self.refresh_words()

    def update_word(self):
        if not self.selected_group:
            return
        self.dict.update_word(
            self.selected_group,
            self.word_entry.get(),
            self.mean_entry.get(),
            self.ex_entry.get()
        )
        self.refresh_words()

    def delete_word(self):
        if not self.selected_group:
            return
        self.dict.delete_word(self.selected_group, self.word_entry.get())
        self.refresh_words()

    def search_words(self):
        query = self.search_var.get()
        results = self.dict.search(query)

        self.word_list.delete(0, tk.END)
        for w, m, e, g in results:
            self.word_list.insert(tk.END, f"{w} ({g})")


def main():
    root = tk.Tk()
    DictManagerUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
