"""Offline output filter: no dose may leave the phone from the small model. See docs/kiran/DECISIONS.md D5.

Blocks a number (ASCII or Devanagari digits, ranges, decimals) next to a unit, a spelled-out number
(Latin or Devanagari) next to a unit, and spoken measures ("do chammach"). Over-blocking is intended:
"50 kg seed" is blocked too, because the cost of a wrong dose is far higher than one extra cloud call.
"""
import re

W = r"[\wऀ-ॿ]"
NUM = r"[0-9०-९]+(?:[.,/][0-9०-९]+)?"
UNITS = [
    "ml", "mls", "mi\\.?\\s?li", "मि\\.?\\s?ली", "मिली", "मिलीलीटर", "मिलि", "milli?litre", "milliliter",
    "l", "ltr", "ltrs", "lt", "litre", "litres", "liter", "liters", "लीटर", "लिटर", "ली\\.", "ली॰",
    "kg", "kgs", "kilo", "kilos", "किलो", "किलोग्राम", "किग्रा", "कि\\.ग्रा\\.?",
    "g", "gm", "gms", "gram", "grams", "gramme", "ग्राम", "ग्रा\\.", "mg", "मिलीग्राम",
    "ppm", "%", "percent", "प्रतिशत", "फीसदी",
    "quintal", "क्विंटल", "tonne", "ton", "टन",
    "tsp", "tbsp", "teaspoon", "tablespoon", "cup", "glass", "bottle", "packet", "cap", "lid",
    "chammach", "chamach", "chamcha", "चम्मच", "चमचा", "चमच",
    "dhakkan", "dhakan", "ढक्कन", "mutthi", "मुट्ठी", "gilas", "गिलास", "botal", "बोतल", "पैकेट",
    "bori", "बोरी", "bag", "थैला", "tablet", "goli", "गोली", "paav", "पाव", "seer", "सेर",
]
SPOKEN = [
    "ek", "do", "teen", "char", "chaar", "paanch", "panch", "chhe", "chhah", "saat", "aath", "nau", "das",
    "aadha", "adha", "aadhi", "dedh", "dhai", "dhaai", "sawa", "savva", "saade", "saadhe", "paune", "pauna",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "half", "quarter",
    "एक", "दो", "तीन", "चार", "पांच", "पाँच", "छह", "छः", "सात", "आठ", "नौ", "दस",
    "आधा", "आधी", "डेढ़", "ढाई", "सवा", "साढ़े", "पौना", "पौन",
]
_u = "(?:" + "|".join(UNITS) + ")"
_unit_end = rf"(?!{W})"
_PATTERNS = [
    re.compile(rf"(?<![0-9०-९.,]){NUM}(?:\s*(?:-|–|से|to)\s*{NUM})?\s*{_u}{_unit_end}", re.I),
    re.compile(rf"(?<!{W})(?:पाव|paav|सेर|seer)\s+(?:भर|bhar){_unit_end}", re.I),  # "paav bhar dawa"
    re.compile(rf"(?<!{W})(?:{'|'.join(SPOKEN)})\s+(?:{W}+\s+)?{_u}{_unit_end}", re.I),
]

DEFERRAL = {
    "hi": "सही मात्रा बताना यहाँ सुरक्षित नहीं है। कृपया कृषि विशेषज्ञ या KCC 1551 से पूछें; इंटरनेट आने पर हम जवाब भेज देंगे।",
    "en": "I can't safely give an exact quantity offline. Please ask an agriculture expert or KCC 1551; we will send a checked answer when you are online.",
}


def check(text):
    """(blocked, matched_text)."""
    for rx in _PATTERNS:
        m = rx.search(text or "")
        if m:
            return True, m.group(0)
    return False, None


def apply(text, lang="hi"):
    """Returns (text_to_show, blocked)."""
    blocked, _ = check(text)
    return (DEFERRAL["hi" if lang == "hi" else "en"], True) if blocked else (text, False)
