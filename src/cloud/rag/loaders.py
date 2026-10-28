import re
import unicodedata
from pathlib import Path


def load_text(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        text = "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    elif suffix in (".html", ".htm"):
        from bs4 import BeautifulSoup
        html = path.read_text(encoding="utf-8", errors="ignore")
        text = BeautifulSoup(html, "html.parser").get_text("\n")
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
    return normalize(text)


def normalize(text):
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()
