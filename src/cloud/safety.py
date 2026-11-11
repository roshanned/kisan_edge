"""Cloud safety filter (PLAN.md Phase 2, Sai step 2): doses only from cited sources, banned products refused.

Works per sentence on the final answer. A sentence that
  - names a banned pesticide is replaced by a refusal;
  - contains a dose (number + unit, same detector as the offline filter) but cites no retrieved source or tool is replaced by a deferral.
Citations are '[doc_id]' (retrieved chunk) or '[tool:<name>]' (tool that was actually called).
Weather exception (Nov 11): when the weather tool returned data, a sentence about the weather ("84% chance of rain")
that names no chemical is kept even without a per-sentence citation. Without it, 81% of tool-backed weather answers
lost their forecast to the dose detector, whose units include "%".
"""
import re
from pathlib import Path

from src.router_gate.safety_filter import check as has_dose

BANNED = [t.strip() for t in (Path(__file__).parent / "banned_pesticides.txt").read_text(encoding="utf-8").splitlines()
          if t.strip() and not t.startswith("#")]
_BANNED_RX = re.compile(r"(?<![a-z])(" + "|".join(map(re.escape, BANNED)) + r")(?![a-z])", re.I)
REFUSE = "यह कीटनाशक भारत में प्रतिबंधित है, इसका उपयोग न करें। सही विकल्प के लिए KCC 1551 पर पूछें। / This pesticide is banned in India; do not use it. Ask KCC 1551 for an alternative."
DEFER = "सही मात्रा के लिए कृषि विशेषज्ञ या KCC 1551 से पूछें। / For the exact quantity please ask an agriculture expert or KCC 1551."
SPLIT = re.compile(r"(?<=[.!?।])\s+|\n+")
WEATHER = re.compile(r"rain|temperature|forecast|humid|wind|cloud|°|mm\b|barish|baarish|mausam|tapman|बारिश|वर्षा|तापमान|"
                     r"मौसम|पूर्वानुमान|नमी|आर्द्रता|हवा|बादल|डिग्री|मिमी|संभावना", re.I)
CHEMICAL = re.compile(r"spray|pesticide|insecticide|fungicide|herbicide|weedicide|fertili[sz]er|urea|dap|potash|dawa|dawai|"
                      r"छिड़काव|कीटनाशक|फफूंदनाशक|खरपतवारनाशक|उर्वरक|यूरिया|डीएपी|पोटाश|दवा|दवाई", re.I)


def apply(text, allowed):
    """allowed = set of ids that count as sources (retrieved doc_ids + 'tool:<name>'). Returns (text, events)."""
    weather_ok = "tool:get_weather" in allowed
    out, events = [], []
    for s in SPLIT.split(text or ""):
        if not s.strip():
            continue
        cited = set(re.findall(r"\[([^\[\]]+)\]", s)) & allowed
        if m := _BANNED_RX.search(s):
            out.append(REFUSE)
            events.append({"type": "banned", "match": m.group(0)})
        elif has_dose(s)[0] and not cited and not (weather_ok and WEATHER.search(s) and not CHEMICAL.search(s)):
            out.append(DEFER)
            events.append({"type": "uncited_dose", "match": has_dose(s)[1]})
        else:
            out.append(s)
    seen, final = set(), []
    for s in out:  # collapse repeated refusals/deferrals
        if s in (REFUSE, DEFER) and s in seen:
            continue
        seen.add(s)
        final.append(s)
    return " ".join(final), events
