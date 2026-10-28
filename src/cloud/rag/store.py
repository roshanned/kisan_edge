import json
import sqlite3
from pathlib import Path

import faiss
import numpy as np

from src.cloud.rag.dedup import content_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
    doc_id TEXT PRIMARY KEY, doc_key TEXT, source TEXT, date TEXT,
    lang TEXT, title TEXT, path TEXT, hash TEXT UNIQUE, text TEXT
);
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY, doc_id TEXT, idx INTEGER, text TEXT, hash TEXT
);
CREATE TABLE IF NOT EXISTS embeddings (hash TEXT PRIMARY KEY, vec BLOB);
"""


class Store:
    def __init__(self, index_dir):
        self.dir = Path(index_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.dir / "rag.sqlite")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def get_doc(self, doc_id):
        row = self.db.execute("SELECT * FROM docs WHERE doc_id = ?", (doc_id,)).fetchone()
        return dict(row) if row else None

    def find_by_hash(self, h):
        row = self.db.execute("SELECT doc_id FROM docs WHERE hash = ?", (h,)).fetchone()
        return row[0] if row else None

    def all_docs(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM docs")]

    def add_doc(self, doc, chunks):
        self.db.execute(
            "INSERT INTO docs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (doc["doc_id"], doc.get("doc_key"), doc["source"], doc["date"], doc["lang"],
             doc.get("title"), doc["path"], doc["hash"], doc["text"]),
        )
        self.db.executemany(
            "INSERT INTO chunks VALUES (?, ?, ?, ?, ?)",
            [(f"{doc['doc_id']}#{i}", doc["doc_id"], i, t, content_hash(t)) for i, t in enumerate(chunks)],
        )
        self.db.commit()

    def active_doc_ids(self, as_of=None):
        # Within a doc_key only the newest doc (up to as_of) stays active.
        latest, active = {}, []
        rows = self.db.execute(
            "SELECT doc_id, doc_key FROM docs WHERE ? IS NULL OR date <= ? ORDER BY date, doc_id",
            (as_of, as_of),
        )
        for r in rows:
            if r["doc_key"]:
                latest[r["doc_key"]] = r["doc_id"]
            else:
                active.append(r["doc_id"])
        return active + list(latest.values())

    def active_chunks(self, as_of=None):
        ids = self.active_doc_ids(as_of)
        marks = ",".join("?" * len(ids))
        rows = self.db.execute(
            f"SELECT chunk_id, text, hash FROM chunks WHERE doc_id IN ({marks}) ORDER BY doc_id, idx", ids
        )
        return [dict(r) for r in rows]

    def get_chunk(self, chunk_id):
        row = self.db.execute(
            "SELECT c.chunk_id, c.doc_id, c.text, d.source, d.date, d.lang, d.title "
            "FROM chunks c JOIN docs d USING (doc_id) WHERE c.chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        return dict(row)

    def get_embeddings(self, hashes):
        out = {}
        for h in hashes:
            row = self.db.execute("SELECT vec FROM embeddings WHERE hash = ?", (h,)).fetchone()
            if row:
                out[h] = np.frombuffer(row[0], dtype="float32")
        return out

    def save_embeddings(self, hashes, vecs):
        self.db.executemany(
            "INSERT OR REPLACE INTO embeddings VALUES (?, ?)",
            [(h, v.tobytes()) for h, v in zip(hashes, vecs)],
        )
        self.db.commit()

    def save_index(self, index, chunk_ids):
        faiss.write_index(index, str(self.dir / "faiss.index"))
        (self.dir / "ids.json").write_text(json.dumps(chunk_ids))

    def load_index(self):
        index = faiss.read_index(str(self.dir / "faiss.index"))
        return index, json.loads((self.dir / "ids.json").read_text())
