"""Kaggle job 05: OCR scanned Hindi PDFs for the RAG corpus (no text layer, so pypdf gets nothing).

UP government sites do not answer from Kaggle, so download the PDF locally into corpus/raw/<doc_id>.pdf
(URLs in OCR_DOCS in src/cloud/fetch_corpus.py) and ship it with the corpus dataset:
  python kaggle/push_corpus.py "msg"
  kaggle kernels push -p kaggle/jobs/05_ocr
  kaggle kernels output roshanned/kisan-edge-05-ocr -p kaggle/results/05_ocr
Then copy kaggle/results/05_ocr/*.txt to corpus/raw/ and rerun fetch_corpus (it lists them in docs.jsonl).

Output: <doc_id>.txt per PDF, pages separated by blank lines.
"""
import glob
import os
import subprocess
import zipfile

DOCS = []  # same ids as OCR_DOCS in src/cloud/fetch_corpus.py
WORK = "/kaggle/working"


def sh(cmd):
    print(f"\n$ {cmd}", flush=True)
    subprocess.run(cmd, shell=True, check=True)


def main():
    sh("apt-get -qq update && apt-get -qq install -y tesseract-ocr tesseract-ocr-hin poppler-utils > /dev/null")
    sh("pip install -q pytesseract pdf2image")
    import pytesseract
    from pdf2image import convert_from_path

    docs = glob.glob("/kaggle/input/**/docs.jsonl", recursive=True)
    if not docs:
        raise SystemExit("kisan-edge-corpus dataset not attached")
    raw = os.path.join(os.path.dirname(docs[0]), "raw")
    if not os.path.isdir(raw):
        with zipfile.ZipFile(raw + ".zip") as z:
            z.extractall("/tmp/raw")
        raw = "/tmp/raw"
    for doc_id in DOCS:
        pdf = f"{raw}/{doc_id}.pdf"
        pages = convert_from_path(pdf, dpi=300)
        text = "\n\n".join(pytesseract.image_to_string(p, lang="hin+eng") for p in pages)
        with open(f"{WORK}/{doc_id}.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"{doc_id}: {len(pages)} pages, {len(text)} chars", flush=True)


if __name__ == "__main__":
    main()
