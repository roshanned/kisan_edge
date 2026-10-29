"""Rule router + optional intent classifier. See docs/kiran/README.md.

Order: emergency rules > high_risk rules > live_data rules > classifier (if trained) > 'general'.
Everything except 'general' is always sent to the cloud; the gate only judges 'general' questions.
"""
import re
from functools import lru_cache
from pathlib import Path

KW_DIR = Path(__file__).parent / "keywords"
W = r"[\wऀ-ॿ]"  # Python's \w drops Devanagari vowel signs, so spell the class out
# Shown whenever the question is an emergency, in every language and whether or not the link is up.
EMERGENCY_NUMBERS = "108 (ambulance), 112 (emergency), KCC 1551"
CLF_SAFETY_MASS = 0.35  # if P(high_risk)+P(emergency) >= this, the classifier picks the riskier class


def _compile(name, whole_word):
    terms = [t.strip() for t in (KW_DIR / f"{name}.txt").read_text(encoding="utf-8").splitlines()]
    pats = []
    for t in terms:
        if not t or t.startswith("#"):
            continue
        exact = t.endswith("$")
        t = t.rstrip("$")
        pats.append(rf"(?<!{W}){re.escape(t.lower())}" + (rf"(?!{W})" if whole_word or exact else ""))
    return re.compile("|".join(pats))


@lru_cache(maxsize=1)
def _rules():
    return [("emergency", _compile("emergency", True)),
            ("high_risk", _compile("high_risk", False)),
            ("live_data", _compile("live_data", False))]


def rule_route(question):
    """(category, matched_text) from the keyword lists, or (None, None)."""
    q = question.lower()
    for cat, rx in _rules():
        m = rx.search(q)
        if m:
            return cat, m.group(0)
    return None, None


class Router:
    def __init__(self, clf=None):
        self.clf = clf  # sklearn Pipeline from intent_clf.train(), or None for rules only

    def route(self, question):
        cat, hit = rule_route(question)
        if cat:
            return {"category": cat, "reason": f"rule:{hit}"}
        if self.clf is not None:
            proba = dict(zip(self.clf.classes_, self.clf.predict_proba([question])[0]))
            risky = {c: proba.get(c, 0) for c in ("high_risk", "emergency")}
            if sum(risky.values()) >= CLF_SAFETY_MASS:
                return {"category": max(risky, key=risky.get), "reason": "clf:safety"}
            return {"category": max(proba, key=proba.get), "reason": "clf"}
        return {"category": "general", "reason": "default"}


if __name__ == "__main__":
    # Writes outputs/router.jsonl (PLAN.md section 5): the route for every test question, before any gate or queue.
    from src.common.schemas import check
    from src.data.common import read_jsonl, write_jsonl
    from src.router_gate import intent_clf
    r = Router(intent_clf.load())
    rows = [check("router", {"id": q["id"], "route": (x := r.route(q["question"]))["category"], "gate_score": None,
                             "kept_offline": None, "final_answer": None, "answered_by": None, "queued_at": None,
                             "delivered_at": None, "route_reason": x["reason"]})
            for q in read_jsonl("data/processed/questions.jsonl") if q["split"] == "test"]
    write_jsonl(rows, "outputs/router.jsonl")
    print(f"wrote {len(rows)} routes to outputs/router.jsonl")
