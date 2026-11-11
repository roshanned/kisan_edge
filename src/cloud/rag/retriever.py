import threading

from src.cloud.rag.embed import embed
from src.cloud.rag.store import Store


class Retriever:
    def __init__(self, index_dir="corpus/index"):
        self.store = Store(index_dir)
        self.index, self.ids = self.store.load_index()
        self.lock = threading.Lock()  # the embedder and the SQLite store are shared by query.py --workers threads

    def search(self, query, k=5):
        if not self.ids:
            return []
        with self.lock:
            scores, rows = self.index.search(embed([query]), k)
            return [
                {**self.store.get_chunk(self.ids[r]), "score": float(s)}
                for s, r in zip(scores[0], rows[0]) if r != -1
            ]
