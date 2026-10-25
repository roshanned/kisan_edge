"""Shared cleaning helpers and the question record format (PLAN.md section 5)."""
import hashlib
import html
import json
import re
from pathlib import Path

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
LATIN = re.compile(r"[A-Za-z]")
MOJIBAKE = re.compile(r"\?{3,}")  # answers whose Devanagari was lost as "????"
PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
SPACES = re.compile(r"\s+")

# Common romanised-Hindi words. Two or more hits in a Latin-script text => Hinglish.
HINGLISH_WORDS = set("""
ki ke ka ko me mein main mai hai hain he ho hota hoti rha rhi raha rahi rahe kya kaise kab kaun kitna kitni
kare karen kre karna karein karo kar diya dena dene liye lie se par pe aur ya bhi nahi nhi na
bataye batayen bataiye batao jankari jaankari chahiye chahte chahta chate sakte sakta
dhan dhaan gehu gehun gehoon ganna ganne sarso sarson sarason fasal kheti khet beej bij bij
khad khaad urea dawa dawai dava rog keet kida kide ghas ghaas patti pati pattiyan jad jadd tana
peela pila pili lal sukh sookh sukh gal sad lag lage laga chhidkav chidkav spray pani paani
bimari upchar ilaj prajati kisan bhai ji shriman apke aapke yaha yahan agami barish
""".split())
# Hindi grammar words that almost never appear in English; one of these is enough
# (catches code-mixed questions like "fertilizer ki problem of paddy crop").
HINGLISH_STRONG = set("ki ke ka hai hain kya kaise kare kre karen karna nahi nhi rha rhi raha rahi liye bataye batayen".split())

CROP_ALIASES = {
    "wheat": ["wheat", "gehu", "gehun", "gehoon", "gehoo", "गेहूं", "गेहूँ", "गेंहू"],
    "paddy": ["paddy", "rice", "dhan", "dhaan", "धान"],
    "mustard": ["mustard", "sarso", "sarson", "rapeseed", "सरसों", "सरसो", "राई"],
    "sugarcane": ["sugarcane", "ganna", "ganne", "गन्ना", "गन्ने"],
}

# First-pass category from KCC QueryType. Kiran owns the final router labels;
# this is only so every record has a category from day one.
LIVE_DATA_TYPES = {"Weather", "Market Information", "Government Schemes", "Crop Insurance",
                   "Sowing Time and Weather"}
HIGH_RISK_TYPES = {"Plant Protection", "Fertilizer Use and Availability", "Nutrient Management",
                   "Weed Management", "Disease Management", "Credit", "Bio-Pesticides and Bio-Fertilizers"}
EMERGENCY_WORDS = ["poison", "zeher", "jahar", "zahar", "जहर", "ज़हर", "behosh", "बेहोश", "ulti", "उल्टी"]
# KCC QueryType is noisy (weather questions tagged "Plant Protection"), so these words win over it.
LIVE_DATA_WORDS = ["weather", "mausam", "mosam", "forecast", "barish", "barsat", "rain", "mandi", "bhav",
                   "price", "yojana", "yojna", "scheme", "subsidy", "anudan", "insurance", "bima", "beema",
                   "मौसम", "पूर्वानुमान", "बारिश", "वर्षा", "मंडी", "भाव", "योजना", "सब्सिडी", "अनुदान", "बीमा"]


LEADING_JUNK = re.compile(r"^[^\wऀ-ॿ]+")  # "--Information about..." / "?Information..."


def norm(text):
    # Some KCC rows store Devanagari as HTML entities (&#2350;...); decode them first.
    text = SPACES.sub(" ", html.unescape(str(text or ""))).strip()
    return LEADING_JUNK.sub("", text)


def remove_phones(text):
    return PHONE.sub("[PHONE]", text)


def detect_script(text):
    """Returns (lang, script): ('hi','deva'), ('hi','latn') for Hinglish, or ('en','latn')."""
    if DEVANAGARI.search(text):
        return "hi", "deva"
    words = re.findall(r"[a-z]+", text.lower())
    hits = sum(w in HINGLISH_WORDS for w in words)
    if hits >= 2 or any(w in HINGLISH_STRONG for w in words) or (words and hits / len(words) >= 0.3):
        return "hi", "latn"
    return "en", "latn"


def find_crop(*texts):
    blob = " ".join(texts).lower()
    for crop, aliases in CROP_ALIASES.items():
        if any(re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", blob) for a in aliases):
            return crop
    return None


def category_for(query_type, question):
    q = question.lower()
    if any(re.search(rf"(?<![a-zऀ-ॿ]){re.escape(w)}(?![a-zऀ-ॿ])", q) for w in EMERGENCY_WORDS):
        return "emergency"
    if query_type in LIVE_DATA_TYPES or any(re.search(rf"(?<![a-z]){re.escape(w)}", q) for w in LIVE_DATA_WORDS):
        return "live_data"
    if query_type in HIGH_RISK_TYPES:
        return "high_risk"
    return "general"


def make_id(source, question, answer):
    h = hashlib.sha1(f"{question.lower()}||{answer.lower()}".encode("utf-8")).hexdigest()[:12]
    return f"{source}_{h}"


def record(source, question, answer, lang, script, crop, query_type, category,
           district=None, year=None, answer_script=None):
    return {
        "id": make_id(source, question, answer),
        "split": None,  # filled once by Anushka's split script
        "lang": lang,
        "script": script,
        "crop": crop,
        "query_type": query_type,
        "category": category,
        "district": district,
        "question": question,
        "reference_answer": answer,
        "answer_script": answer_script,
        "year": year,
        "source": source,
        "gold": False,
    }


def write_jsonl(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
