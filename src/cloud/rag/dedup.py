import hashlib

from datasketch import MinHash

NUM_PERM = 128


def content_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def minhash(text, n=3):
    words = text.split()
    shingles = [" ".join(words[i:i + n]).encode("utf-8") for i in range(max(1, len(words) - n + 1))]
    m = MinHash(num_perm=NUM_PERM)
    m.update_batch(shingles)
    return m
