import re
PATTERNS = [
    re.compile(r"[\w.+-]+\s*(@|\(at\)|\[at\])\s*[\w-]+\s*(\.|\(dot\)|\[dot\])\s*[\w.]+", re.I),
    re.compile(r"(https?://|www\.)\S+", re.I),
    re.compile(r"\b[\w-]+\.(com|ir|net|org|co|info|me|io)\b", re.I),
    re.compile(r"(t\.me|wa\.me|instagram\.com|telegram\.me)\S*", re.I),
    re.compile(r"(?<!\w)@[A-Za-z0-9_]{4,}"),
    re.compile(r"(تلگرام|واتساپ|واتس\s?اپ|اینستاگرام|ایتا|روبیکا|whatsapp|telegram|instagram|ایمیل|شماره\s?تماس|آدرس\s?دقیق)", re.I),
]
MASK = "[اطلاعات تماس حذف شد]"
def redact(text: str):
    """returns (clean_text, was_flagged). Best-effort: pair with admin review."""
    out, flagged = text, False
    for p in PATTERNS:
        out, n = p.subn(MASK, out); flagged |= n > 0
    out, n = re.subn(r"(?:[0-9۰-۹٠-٩][\s\-().]*){8,}", MASK, out); flagged |= n > 0
    return out, flagged
