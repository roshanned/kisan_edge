import pytest

from src.eval.judge import mock_judge, parse
from src.eval.judge_check import kappa
from src.eval.report import wilson


def test_parse_accepts_fenced_json_and_normalises_label():
    r = parse('```json\n{"label": "Partly correct", "deferred": false, "reason": "ok"}\n```')
    assert r["label"] == "partly_correct" and r["deferred"] is False


def test_parse_rejects_unknown_label():
    with pytest.raises(ValueError):
        parse('{"label": "maybe"}')


def test_mock_judge_extremes():
    q = {"reference_answer": "यूरिया डालें दो बार"}
    assert mock_judge(q, "यूरिया डालें दो बार")["label"] == "correct"
    assert mock_judge(q, "xyz")["label"] == "wrong"


def test_kappa_perfect_and_chance():
    assert kappa([("correct", "correct"), ("wrong", "wrong")]) == 1.0
    assert abs(kappa([("correct", "wrong"), ("wrong", "correct")]) - (-1.0)) < 1e-9


def test_wilson_bounds():
    lo, hi = wilson(50, 100)
    assert 0.39 < lo < 0.41 and 0.59 < hi < 0.61
    assert wilson(0, 0) == (0.0, 0.0)
