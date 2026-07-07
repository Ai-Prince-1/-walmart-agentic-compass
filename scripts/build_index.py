"""Build the corpus index: PDFs -> chunked JSON with source + page citations.

Deliberately simple (spec §4): no vector DB, no embeddings. A scored keyword
search over ~1,200-char chunks is sufficient for a closed, trusted corpus and
keeps the token/dependency footprint minimal (Day 3: token-economy discipline).
Run once; commit corpus_index/chunks.json.
"""
import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
OUT = ROOT / "corpus_index" / "chunks.json"

CHUNK_SIZE = 1200
OVERLAP = 150


def clean(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\x00", " ")).strip()


def chunk_page(text: str):
    text = clean(text)
    if not text:
        return
    step = CHUNK_SIZE - OVERLAP
    for start in range(0, max(len(text) - OVERLAP, 1), step):
        piece = text[start:start + CHUNK_SIZE].strip()
        if len(piece) > 80:  # skip crumbs
            yield piece


def main():
    chunks = []
    for pdf in sorted(CORPUS.glob("*.pdf")):
        reader = PdfReader(str(pdf))
        for page_no, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            for piece in chunk_page(text):
                chunks.append({"source": pdf.name, "page": page_no, "text": piece})
        print(f"indexed {pdf.name}: {len(reader.pages)} pages")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(chunks, ensure_ascii=False))
    print(f"wrote {len(chunks)} chunks -> {OUT}")


if __name__ == "__main__":
    main()
