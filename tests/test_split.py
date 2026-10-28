"""Checks on the frozen split. Run after src.data.build_questions: pytest tests/test_split.py"""
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

Q = Path("data/processed/questions.jsonl")
pytestmark = pytest.mark.skipif(not Q.exists(), reason="questions.jsonl not built")


def rows():
    return [json.loads(line) for line in Q.open(encoding="utf-8")]


def qkey(t):
    return " ".join(str(t).lower().split()).rstrip(" ?.!")


def test_ids_unique_and_splits_valid():
    r = rows()
    assert len({x["id"] + "|" + x["lang"] + x["script"] for x in r}) == len(r)
    assert {x["split"] for x in r} == {"train", "dev", "calib", "test"}


def test_no_question_text_shared_between_splits():
    by_text = {}
    for x in rows():
        for t in {qkey(x["question"]), qkey(x.get("question_en") or x["question"])}:
            by_text.setdefault(t, set()).add(x["split"])
    leaked = {t for t, s in by_text.items() if len(s) > 1}
    assert not leaked, list(leaked)[:5]


def test_pilot_only_in_dev():
    pilot = set(Path("data/raw/hf/processed/pilot_ids.txt").read_text().split())
    assert {x["split"] for x in rows() if x["id"] in pilot} == {"dev"}


def test_gold_is_test_and_balanced():
    g = [x for x in rows() if x["gold"]]
    assert all(x["split"] == "test" for x in g)
    assert len(g) == 200
    assert set(Counter(x["gold_batch"] for x in g).values()) == {50}


def test_only_our_crops_and_no_phones():
    r = rows()
    assert {x["crop"] for x in r} <= {"wheat", "paddy", "mustard", "sugarcane"}
    import re
    phone = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")
    assert not [x["id"] for x in r if phone.search(x["question"])]


def test_test_set_is_frozen():
    m = json.load(open("data/processed/split_manifest.json"))
    ids = "\n".join(sorted(x["id"] for x in rows() if x["split"] == "test"))
    assert hashlib.sha256(ids.encode()).hexdigest() == m["test_ids_sha256"]
