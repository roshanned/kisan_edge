import re

# Splits after English punctuation and the Hindi danda.
SENTENCE_END = re.compile(r"(?<=[.!?।])\s+")


def chunk_text(text, max_chars=1500, overlap=200):
    chunks, current = [], ""
    for sentence in SENTENCE_END.split(text):
        if current and len(current) + len(sentence) > max_chars:
            chunks.append(current.strip())
            current = current[-overlap:]
        current += " " + sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks
