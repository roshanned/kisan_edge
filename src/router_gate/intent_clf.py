"""Small intent classifier: char n-gram TF-IDF + logistic regression on router_labels (TRAIN split only).

Used by Router only when no keyword rule fires. Model is saved to models/intent_clf.pkl (gitignored; ~10 s to rebuild).
Usage: python -m src.router_gate.intent_clf          -> trains, prints dev accuracy
"""
import pickle
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from src.data.common import read_jsonl

MODEL = Path("models/intent_clf.pkl")


def load_xy(split):
    qs = {q["id"]: q["question"] for q in read_jsonl("data/processed/questions.jsonl")}
    rows = [r for r in read_jsonl("data/processed/router_labels.jsonl") if r["split"] == split]
    return [qs[r["id"]] for r in rows], [r["label"] for r in rows], rows


def train():
    X, y, _ = load_xy("train")  # never dev/calib/test: they are for tuning and reporting
    clf = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3, sublinear_tf=True),
                        LogisticRegression(max_iter=1000, class_weight="balanced", C=3.0))
    return clf.fit(X, y)


def load():
    return pickle.loads(MODEL.read_bytes()) if MODEL.exists() else None


if __name__ == "__main__":
    clf = train()
    MODEL.parent.mkdir(exist_ok=True)
    MODEL.write_bytes(pickle.dumps(clf))
    X, y, _ = load_xy("dev")
    print("dev accuracy", sum(a == b for a, b in zip(clf.predict(X), y)) / len(y), "saved", MODEL)
