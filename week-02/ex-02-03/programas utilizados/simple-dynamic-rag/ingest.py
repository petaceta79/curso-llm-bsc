# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

"""Ingestion — how a document gets into a collection.

Ingestion is the process where a document is added to a collection, in four steps:

  1. CONVERT the document to markdown (here: markitdown — pdf, docx, pptx, html,
     txt... all become md). For scanned documents you would use an OCR model
     instead: mistral-ocr in the cloud, or deepseek-ocr running locally (mlx on
     Apple Silicon, CUDA on NVIDIA).
  2. STORE both the original and its markdown distillation somewhere linkable —
     here `static/` (the same idea as /static in a FastAPI app), so every chunk
     can point back to its document by URL.
  3. CHUNK the markdown — see chunking.py: a sliding window of characters with
     overlap, or the document's own ## sections.
  4. INSERT each chunk into the collection with its metadata: the document url,
     the title, the url of the md distilation, the chunk number, the chunking
     strategy, and the date of ingestion.

Usage:
    uv run ingest.py path/to/document.pdf
    uv run ingest.py handbook.md --strategy sections --level 2
    uv run ingest.py notes.txt   --strategy chars --size 800 --overlap 100
"""
import argparse
import datetime
import shutil
from pathlib import Path

from dotenv import load_dotenv
from markitdown import MarkItDown

from chunking import chunk_by_chars, chunk_by_sections
from collections_manager import create_collection, insert

load_dotenv()

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"


def ingest(path: str, collection_name: str = "handbook", persist_path: str = "./collections-store",
           strategy: str = "chars", size: int = 800, overlap: int = 100, level: int = 2) -> None:
    doc = Path(path)
    if not doc.exists():
        raise SystemExit(f"no such file: {doc}")
    STATIC.mkdir(exist_ok=True)

    # 1 — convert to markdown
    result = MarkItDown().convert(str(doc))
    markdown = result.text_content
    title = (result.title or doc.stem).strip()
    print(f"1. converted {doc.name} -> markdown ({len(markdown)} chars) · title: {title!r}")

    # 2 — store original + distillation where they can be linked
    doc_url = f"static/{doc.name}"
    md_name = f"{doc.stem}.md" if doc.suffix.lower() != ".md" else f"{doc.stem}.distilled.md"
    md_url = f"static/{md_name}"
    shutil.copy(doc, STATIC / doc.name)
    (STATIC / md_name).write_text(markdown, encoding="utf-8")
    print(f"2. stored     {doc_url}  +  {md_url}")

    # 3 — chunk
    if strategy == "sections":
        chunks = chunk_by_sections(markdown, level=level)
        strategy_label = f"sections(level={level})"
    else:
        chunks = chunk_by_chars(markdown, size=size, overlap=overlap)
        strategy_label = f"chars(size={size},overlap={overlap})"
    print(f"3. chunked    {len(chunks)} chunks · strategy {strategy_label}")

    # 4 — insert with metadata
    col = create_collection(collection_name, description="simple-dynamic-rag knowledge",
                            metric="cosine", persist_path=persist_path)
    ok = 0
    for n, chunk in enumerate(chunks):
        r = insert(col, chunk, {
            "source": doc.stem,
            "doc_url": doc_url,
            "md_url": md_url,
            "title": title,
            "chunk_number": n,
            "chunking_strategy": strategy_label,
            "ingested_at": datetime.date.today().isoformat(),
        })
        ok += r["ok"]
        if not r["ok"]:
            print(f"   ✘ chunk {n}: {r['error']}")
    print(f"4. inserted   {ok}/{len(chunks)} chunks into collection {collection_name!r} "
          f"({col.count()} total, persisted at {persist_path})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Ingest a document into a collection.")
    ap.add_argument("files", nargs="+", help="document(s): pdf, docx, md, txt, html...")
    ap.add_argument("--collection", default="handbook")
    ap.add_argument("--persist", default="./collections-store")
    ap.add_argument("--strategy", choices=["chars", "sections"], default="chars")
    ap.add_argument("--size", type=int, default=800, help="chars per chunk (chars strategy)")
    ap.add_argument("--overlap", type=int, default=100, help="shared margin between chunks (chars strategy)")
    ap.add_argument("--level", type=int, default=2, help="heading level to cut at (sections strategy)")
    args = ap.parse_args()
    for f in args.files:
        ingest(f, collection_name=args.collection, persist_path=args.persist,
               strategy=args.strategy, size=args.size, overlap=args.overlap, level=args.level)
