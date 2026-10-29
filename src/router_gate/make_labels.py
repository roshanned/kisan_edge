"""Builds data/processed/router_labels.jsonl from the frozen questions file. See docs/kiran/DECISIONS.md D2.

label = Anushka's first-pass category (from KCC QueryType + keywords), upgraded (never downgraded) to
emergency / high_risk when our keyword rules fire. KCC has almost no emergency rows, so those come from rules.
Usage: python -m src.router_gate.make_labels
"""
from collections import Counter

from src.common.schemas import CATEGORIES
from src.data.common import read_jsonl, write_jsonl
from src.router_gate.router import rule_route


def main():
    out = []
    for q in read_jsonl("data/processed/questions.jsonl"):
        cat, _ = rule_route(q["question"])
        label, src = q["category"], "query_type"
        if cat == "emergency" or (cat == "high_risk" and label == "general"):
            label, src = cat, "keyword_upgrade"
        assert label in CATEGORIES
        out.append({"id": q["id"], "split": q["split"], "lang": q["lang"], "script": q["script"],
                    "query_type": q["query_type"], "label": label, "label_source": src})
    write_jsonl(out, "data/processed/router_labels.jsonl")
    print(Counter(r["label"] for r in out), Counter(r["label_source"] for r in out))


if __name__ == "__main__":
    main()
