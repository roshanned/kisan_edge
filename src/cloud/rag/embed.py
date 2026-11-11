from functools import lru_cache

from sentence_transformers import SentenceTransformer

MODEL = "BAAI/bge-m3"
# HF's safetensors conversion of the same weights (main only has pytorch_model.bin, which transformers refuses
# to load on torch < 2.6). Checked: identical embeddings (cosine 1.0) to the .bin weights used for the index.
REVISION = "refs/pr/130"
DIM = 1024


@lru_cache(maxsize=1)
def get_model():
    return SentenceTransformer(MODEL, revision=REVISION)


def embed(texts):
    vecs = get_model().encode(texts, batch_size=16, normalize_embeddings=True, convert_to_numpy=True)
    return vecs.astype("float32")
