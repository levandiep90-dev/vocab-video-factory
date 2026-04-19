import json
import os
import sys
from typing import Dict, List, Optional, Tuple


def get_base_dir():
    """
    Lấy thư mục gốc để lưu dữ liệu.
    - Nếu chạy file .py: lấy thư mục chứa file này
    - Nếu chạy từ .exe: lấy thư mục chứa file .exe
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
DICT_FILE = os.path.join(BASE_DIR, "dictionary_data.json")


DEFAULT_DICT = {
    "ACTIONS": {
        "run": {
            "meaning": "chạy",
            "example": "I run every morning."
        },
        "walk": {
            "meaning": "đi bộ",
            "example": "I walk to school."
        },
        "jump": {
            "meaning": "nhảy",
            "example": "The boy jumps high."
        },
        "climb": {
            "meaning": "leo trèo",
            "example": "She climbs a tree."
        },
        "eat": {
            "meaning": "ăn",
            "example": "I eat rice."
        },
        "drink": {
            "meaning": "uống",
            "example": "I drink water."
        }
    },
    "ANIMALS": {
        "dog": {
            "meaning": "con chó",
            "example": "The dog is running."
        },
        "cat": {
            "meaning": "con mèo",
            "example": "The cat is sleeping."
        },
        "bird": {
            "meaning": "con chim",
            "example": "A bird can fly."
        },
        "fish": {
            "meaning": "con cá",
            "example": "Fish swim in water."
        },
        "rabbit": {
            "meaning": "con thỏ",
            "example": "The rabbit jumps."
        }
    },
    "FOOD": {
        "apple": {
            "meaning": "quả táo",
            "example": "I eat an apple."
        },
        "banana": {
            "meaning": "quả chuối",
            "example": "She eats a banana."
        },
        "bread": {
            "meaning": "bánh mì",
            "example": "I eat bread."
        },
        "milk": {
            "meaning": "sữa",
            "example": "I drink milk."
        },
        "water": {
            "meaning": "nước",
            "example": "Drink water."
        }
    }
}


class DictionaryLib:
    def __init__(self, file_path: str = DICT_FILE):
        self.file_path = file_path
        self.data: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.load()

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = DEFAULT_DICT.copy()
                self.save()
        else:
            self.data = DEFAULT_DICT.copy()
            self.save()

    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def get_groups(self) -> List[str]:
        return list(self.data.keys())

    def add_group(self, group_name: str) -> bool:
        group_name = group_name.strip()
        if not group_name or group_name in self.data:
            return False
        self.data[group_name] = {}
        self.save()
        return True

    def delete_group(self, group_name: str) -> bool:
        if group_name not in self.data:
            return False
        del self.data[group_name]
        self.save()
        return True

    def rename_group(self, old_name: str, new_name: str) -> bool:
        old_name = old_name.strip()
        new_name = new_name.strip()

        if old_name not in self.data:
            return False
        if not new_name or new_name in self.data:
            return False

        self.data[new_name] = self.data.pop(old_name)
        self.save()
        return True

    def get_words_in_group(self, group_name: str) -> Dict[str, Dict[str, str]]:
        return self.data.get(group_name, {})

    def add_word(self, group_name: str, word: str, meaning: str, example: str) -> bool:
        group_name = group_name.strip()
        word_key = word.strip().lower()

        if not group_name or not word_key:
            return False

        if group_name not in self.data:
            self.data[group_name] = {}

        if word_key in self.data[group_name]:
            return False

        self.data[group_name][word_key] = {
            "meaning": meaning.strip(),
            "example": example.strip()
        }
        self.save()
        return True

    def update_word(self, group_name: str, word: str, meaning: str, example: str) -> bool:
        group_name = group_name.strip()
        word_key = word.strip().lower()

        if group_name not in self.data:
            return False
        if word_key not in self.data[group_name]:
            return False

        self.data[group_name][word_key] = {
            "meaning": meaning.strip(),
            "example": example.strip()
        }
        self.save()
        return True

    def delete_word(self, group_name: str, word: str) -> bool:
        group_name = group_name.strip()
        word_key = word.strip().lower()

        if group_name not in self.data:
            return False
        if word_key not in self.data[group_name]:
            return False

        del self.data[group_name][word_key]
        self.save()
        return True

    def lookup(self, word: str) -> Optional[Tuple[str, str, str]]:
        word_key = word.strip().lower()
        if not word_key:
            return None

        for group_name, words in self.data.items():
            if word_key in words:
                item = words[word_key]
                return item.get("meaning", ""), item.get("example", ""), group_name
        return None

    def search(self, query: str) -> List[Tuple[str, str, str, str]]:
        query = query.strip().lower()
        results = []

        if not query:
            return results

        for group_name, words in self.data.items():
            for word, item in words.items():
                meaning = item.get("meaning", "")
                example = item.get("example", "")

                if query in word.lower() or query in meaning.lower():
                    results.append((word, meaning, example, group_name))

        return results

    def get_all_words(self) -> List[Tuple[str, str, str, str]]:
        results = []
        for group_name, words in self.data.items():
            for word, item in words.items():
                results.append((
                    word,
                    item.get("meaning", ""),
                    item.get("example", ""),
                    group_name
                ))
        return results

    def get_stats(self) -> dict:
        total_groups = len(self.data)
        total_words = sum(len(words) for words in self.data.values())

        group_stats = {}
        for group_name, words in self.data.items():
            group_stats[group_name] = len(words)

        return {
            "total_groups": total_groups,
            "total_words": total_words,
            "groups": group_stats
        }

    def export_json(self, export_path: str) -> bool:
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
            return True
        except Exception:
            return False

    def import_json(self, import_path: str, overwrite: bool = True) -> bool:
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                imported_data = json.load(f)

            if not isinstance(imported_data, dict):
                return False

            if overwrite:
                self.data = imported_data
            else:
                for group_name, words in imported_data.items():
                    if group_name not in self.data:
                        self.data[group_name] = {}
                    for word, item in words.items():
                        self.data[group_name][word] = item

            self.save()
            return True
        except Exception:
            return False

    def to_mini_dict(self) -> Dict[str, Tuple[str, str]]:
        result = {}
        for _, words in self.data.items():
            for word, item in words.items():
                result[word] = (
                    item.get("meaning", ""),
                    item.get("example", "")
                )
        return result


_dict_instance = None


def get_dict() -> DictionaryLib:
    global _dict_instance
    if _dict_instance is None:
        _dict_instance = DictionaryLib()
    return _dict_instance


def lookup_word(word: str) -> Optional[Tuple[str, str, str]]:
    return get_dict().lookup(word)


def search_words(query: str) -> List[Tuple[str, str, str, str]]:
    return get_dict().search(query)


if __name__ == "__main__":
    d = get_dict()
    print("📚 Dictionary file:", DICT_FILE)
    print("📊 Stats:", d.get_stats())
    print("🔎 Lookup 'dog':", d.lookup("dog"))
    print("🔎 Search 'chó':", d.search("chó"))
