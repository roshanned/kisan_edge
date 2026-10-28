from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL = "BAAI/bge-m3"
DIM = 1024


@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer(MODEL)


def embed(texts):
    vecs = get_model().encode(texts, batch_size=16, normalize_embeddings=True, convert_to_numpy=True)
    return vecs.astype("float32")
