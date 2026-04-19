# =========================================================
# AI LOOKUP MODULE
# Hỗ trợ: Gemini API / OpenAI API / Offline fallback
# =========================================================
import urllib.request
import urllib.error
import json

AI_PROVIDER = "gemini"   # "gemini" hoặc "openai"
GEMINI_API_KEY = ""      # Điền API key Gemini vào đây
OPENAI_API_KEY = ""      # Điền API key OpenAI vào đây

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
OPENAI_ENDPOINT  = "https://api.openai.com/v1/chat/completions"

PROMPT_TEMPLATE = """
Bạn là từ điển tiếng Anh - tiếng Việt.
Cho từ tiếng Anh: "{word}"
Hãy trả về JSON theo đúng định dạng sau (không giải thích thêm):
{{
  "meaning": "nghĩa tiếng Việt ngắn gọn",
  "example": "1 câu ví dụ tiếng Anh đơn giản, dưới 10 từ"
}}
"""


def _call_gemini(word, api_key):
    prompt = PROMPT_TEMPLATE.format(word=word)
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    url = f"{GEMINI_ENDPOINT}?key={api_key}"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    # Xóa markdown code block nếu có
    text = text.replace("```json", "").replace("```", "").strip()
    result = json.loads(text)
    return result["meaning"], result["example"]


def _call_openai(word, api_key):
    prompt = PROMPT_TEMPLATE.format(word=word)
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENAI_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    text = data["choices"][0]["message"]["content"].strip()
    text = text.replace("```json", "").replace("```", "").strip()
    result = json.loads(text)
    return result["meaning"], result["example"]


def ai_lookup_word(word, provider=None, gemini_key=None, openai_key=None):
    """
    Tra nghĩa + ví dụ bằng AI.
    Trả về (meaning, example, source)
    source: "gemini" | "openai" | "offline"
    """
    p = provider or AI_PROVIDER
    gk = gemini_key or GEMINI_API_KEY
    ok = openai_key or OPENAI_API_KEY

    try:
        if p == "gemini" and gk:
            meaning, example = _call_gemini(word, gk)
            return meaning, example, "gemini"

        elif p == "openai" and ok:
            meaning, example = _call_openai(word, ok)
            return meaning, example, "openai"

    except Exception as e:
        pass  # Fallback về offline

    # Offline fallback
    meaning, example = lookup_word(word)
    return meaning, example, "offline"
