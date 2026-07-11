# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

"""
🗂️ Collections Explorer — an embeddings database you can poke.

A COLLECTION is a table indexed with embeddings. This demo opens one — persistent
on disk by default, so your chunks are still there when you come back — and lets
you fill it and search it by meaning.

Everything goes through the course's collections_manager utility (three functions:
create_collection / insert / query, on ChromaDB). This demo is also the point:
your application talks to the abstraction layer, not to the engine underneath.

Commands:
    /add <text>        add a chunk (you'll be asked for its source)
    /seed              load example chunks so queries land immediately
    /list              what's in the collection (source · chunk_number · text)
    <any other text>   query the collection by meaning, top-K nearest first
    (empty line)       quit

Run with --memory for a throwaway in-memory collection instead of the on-disk one.
"""
import argparse
import os
from dotenv import load_dotenv

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from collections_manager import create_collection, insert, query

load_dotenv()

# High-contrast theme — matches the context-explorer / embeddings-explorer house style.
BG = "grey23"
ON_BG = f"on {BG}"
TEXT = f"bright_white {ON_BG}"
TEXT_DIM = f"grey84 {ON_BG}"
ACCENT = f"bold cyan1 {ON_BG}"
NUM = f"bright_yellow {ON_BG}"
GOOD = f"bright_green {ON_BG}"
BAD = f"orange1 {ON_BG}"
BORDER = "bright_cyan"

console = Console()

TOP_K = int(os.environ.get("TOP_K", "4"))

SEED = [
    ("acme-handbook", "The warehouse robot's top speed is 2.4 metres per second."),
    ("acme-handbook", "The Pallet Pup carries up to 600 kg and its battery lasts nine hours."),
    ("acme-handbook", "Acme Robotics was founded in 2019 in Girona, Catalonia."),
    ("acme-handbook", "Every Pallet Pup ships with an emergency stop any nearby worker can press."),
    ("recipes", "The recipe needs two eggs and a cup of flour."),
]


def show_intro(col, store: str) -> None:
    body = Text()
    body.append("A ", style=TEXT)
    body.append("collection", style=ACCENT)
    body.append(" is a table indexed with embeddings. This one is ", style=TEXT)
    body.append(store, style=NUM)
    body.append(f" and holds {col.count()} chunks right now.\n\n", style=TEXT)
    body.append("Type text to ", style=TEXT)
    body.append("query by meaning", style=ACCENT)
    body.append(f" (top-{TOP_K}, nearest first). Add knowledge with ", style=TEXT)
    body.append("/add <text>", style=NUM)
    body.append(" — every chunk carries at least its ", style=TEXT)
    body.append("source", style=ACCENT)
    body.append(" and its ", style=TEXT)
    body.append("chunk_number", style=ACCENT)
    body.append(" within that source.\n\n", style=TEXT)
    body.append("/add <text>   /seed   /list   (empty line = quit)", style=TEXT_DIM)
    console.print(Panel(body, title="🗂️ Collections Explorer", border_style="bright_magenta",
                        style=ON_BG, padding=(1, 2)))


def show_insert(result: dict) -> None:
    if result["ok"]:
        console.print(Text(f"  ✔ stored as {result['id']}", style=GOOD))
    else:
        console.print(Text(f"  ✘ not stored — {result['error']}", style=BAD))


def show_hits(question: str, hits: list[dict]) -> None:
    if not hits:
        console.print(Text("  (collection is empty — /add or /seed first)", style=BAD))
        return
    table = Table(box=box.SIMPLE_HEAVY, style=ON_BG, header_style=ACCENT,
                  title=f"nearest to: “{question}”", title_style=TEXT_DIM)
    score_name = "similarity" if "similarity" in hits[0] else "distance"
    table.add_column(score_name, justify="right", style=NUM)
    table.add_column("source", style=TEXT_DIM)
    table.add_column("#", justify="right", style=TEXT_DIM)
    table.add_column("chunk", style=TEXT)
    for h in hits:
        m = h["metadata"]
        table.add_row(f"{h[score_name]:.3f}", str(m.get("source", "?")),
                      str(m.get("chunk_number", "?")), h["chunk"])
    console.print(table)


def main() -> None:
    ap = argparse.ArgumentParser(description="Poke an embeddings collection.")
    ap.add_argument("--memory", action="store_true", help="in-memory collection (gone on quit)")
    ap.add_argument("--name", default="playground", help="collection name (default: playground)")
    args = ap.parse_args()

    persist = None if args.memory else os.environ.get("PERSIST_PATH", "./collections-store")
    col = create_collection(args.name, description="collections-explorer playground",
                            metric="cosine", persist_path=persist)
    store = "in memory (gone when you quit)" if args.memory else f"persisted on disk at {persist}"
    show_intro(col, store)

    while True:
        try:
            line = console.input("[bold bright_cyan]📝 > [/bold bright_cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        if line.startswith("/add"):
            chunk = line[4:].strip()
            if not chunk:
                console.print(Text("  usage: /add <text of the chunk>", style=BAD))
                continue
            source = console.input("[bold bright_cyan]   source? [/bold bright_cyan]").strip() or "manual"
            show_insert(insert(col, chunk, {"source": source}))
        elif line == "/seed":
            for source, chunk in SEED:
                show_insert(insert(col, chunk, {"source": source}))
        elif line == "/list":
            got = col._chroma.get()
            rows = sorted(zip(got["metadatas"], got["documents"]),
                          key=lambda r: (str(r[0].get("source")), r[0].get("chunk_number", 0)))
            for meta, doc in rows:
                console.print(Text(f"  {meta.get('source')} · {meta.get('chunk_number')} · {doc}", style=TEXT_DIM))
            console.print(Text(f"  ({col.count()} chunks)", style=NUM))
        else:
            show_hits(line, query(col, line, top_k=TOP_K))

    console.print(Text("bye — the on-disk collection keeps everything for next time.", style=TEXT_DIM))


if __name__ == "__main__":
    main()
