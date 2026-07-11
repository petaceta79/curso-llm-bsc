# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

# =============================================================================================================== #
# Universitat Politècnica de Catalunya (UPC)                                                                      #
# =============================================================================================================== #

"""
📚 Embeddings-RAG Explorer — the whole dynamic-RAG loop, panel by panel.

At startup, the demo INGESTS knowledge.txt: chunks it (a sliding window with
overlap — chunking is a for-loop) and inserts every chunk into a collection
through the course's collections_manager. The same three calls everything this
week is built on: this demo, the collections-explorer, the provided
simple-dynamic-rag tool and YOUR final project all speak the same interface.

Then, every turn, you watch dynamic RAG happen:

    🖥️  CHAT UI        sends:  history (bare) + your latest message
                                  |
                                  v
    🛠️  ASSISTANT ENDPOINT  (STATELESS)
            1. your message becomes the QUERY
            2. the collection returns the nearest chunks (top-K, over a threshold)
            3. builds: [system] + [history] + [ template(your message, THOSE chunks) ]
                                  |
                                  v
    🧠  LLM            returns:  the response only
                                  ^
    🖥️  CHAT UI        appends (your message, response) to history   ✗ chunks NOT saved

In-chat commands:
    /topk N      change how many chunks are retrieved
    /threshold X change the similarity gate (chunks below it are dropped)
    (empty line) quit

The collection lives in memory and is rebuilt from knowledge.txt on every run —
every take of the demo starts identical. Set PERSIST_PATH in .env to keep it.
"""
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich import box

from collections_manager import create_collection, insert, query

load_dotenv()

# High-contrast Rich theme — matches the context-explorer house style.
BG = "grey23"
ON_BG = f"on {BG}"
TEXT = f"bright_white {ON_BG}"
TEXT_DIM = f"grey84 {ON_BG}"
ACCENT = f"bold cyan1 {ON_BG}"
NUM = f"bright_yellow {ON_BG}"
GOOD = f"bright_green {ON_BG}"
BAD = f"orange1 {ON_BG}"

console = Console()

client = OpenAI(
    base_url=os.environ.get("OPENAI_ENDPOINT", "http://localhost:11434/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "ollama"),
)
MODEL = os.environ.get("MODEL", "qwen3:1.7b")

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "320"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "40"))

SYSTEM = "Answer using only the context. If it is not there, say you don't know."
TEMPLATE = "Context:\n----\n{context}\n----\n\nQuestion: {user_input}"

# Suggested questions, in a demo-friendly order. Each one showcases a beat:
# meaning-not-words, a paraphrase, provenance across domains, and finally the
# threshold lesson (the off-topic question).
SUGGESTIONS = [
    "how quick is the delivery robot?",            # words not in the text — retrieval by meaning
    "what does the night drone do?",               # 'night drone' appears nowhere; Shelf Owl wins
    "how long does an installation take?",         # a different chunk entirely
    "what does a Pallet Pup cost, with the dock?", # pricing across two chunks
    "can it work inside a freezer?",               # nuanced answer (Arctic, 2027)
    "give me a noodle recipe",                     # off-topic — watch the threshold, then /threshold 0.5
]


def chunk(text: str, size: int, overlap: int) -> list[str]:
    """Slide a window of `size` characters across the text, stepping by size-overlap."""
    step = max(1, size - overlap)
    pieces = []
    i = 0
    while i < len(text):
        piece = text[i:i + size].strip()
        if piece:
            pieces.append(piece)
        i += step
    return pieces


def _truncate(text: str, width: int = 70) -> str:
    one = " ".join(text.split())
    return one if len(one) <= width else one[: width - 1] + "…"


def show_ui_send(history: list, user_input: str) -> None:
    body = Text()
    body.append("The chat UI sends the BARE conversation — no system prompt, no chunks:\n\n", style=TEXT_DIM)
    for m in history:
        body.append(f"  {m['role']:9s} ", style=ACCENT)
        body.append(_truncate(m["content"]) + "\n", style=TEXT_DIM)
    body.append(f"  user      ", style=ACCENT)
    body.append(user_input + "\n", style=TEXT)
    console.print(Panel(body, title="🖥️ 1 · what the CHAT UI sends", border_style="bright_cyan",
                        style=ON_BG, padding=(0, 1)))


def show_retrieval(user_input: str, kept: list, dropped: list, top_k: int, threshold: float) -> None:
    table = Table(box=box.SIMPLE_HEAVY, style=ON_BG, header_style=ACCENT,
                  title=f"query = the user message · top-{top_k} · threshold {threshold}",
                  title_style=TEXT_DIM)
    table.add_column("similarity", justify="right", style=NUM)
    table.add_column("source", style=TEXT_DIM)
    table.add_column("#", justify="right", style=TEXT_DIM)
    table.add_column("chunk", style=TEXT)
    table.add_column("", style=GOOD)
    for h in kept:
        m = h["metadata"]
        table.add_row(f"{h['similarity']:.3f}", str(m.get("source")), str(m.get("chunk_number")),
                      _truncate(h["chunk"], 56), "→ injected")
    for h in dropped:
        m = h["metadata"]
        table.add_row(Text(f"{h['similarity']:.3f}", style=BAD), str(m.get("source")),
                      str(m.get("chunk_number")), Text(_truncate(h["chunk"], 56), style=TEXT_DIM),
                      Text("✗ below threshold", style=BAD))
    console.print(Panel(table, title="🔎 2 · RETRIEVAL — the collection chooses the context",
                        border_style="bright_magenta", style=ON_BG, padding=(0, 1)))


def show_api_request(messages: list) -> None:
    payload = json.dumps({"model": MODEL, "messages": messages}, indent=2, ensure_ascii=False)
    if len(payload) > 2400:
        payload = payload[:2400] + "\n  ... (truncated for display)"
    console.print(Panel(Syntax(payload, "json", background_color="grey11", word_wrap=True),
                        title="🧠 3 · what we actually send to the LLM",
                        border_style="bright_yellow", style=ON_BG, padding=(0, 1)))


def show_response(answer: str, usage, kept: int, total: int) -> None:
    body = Text()
    body.append(answer + "\n\n", style=TEXT)
    body.append(f"prompt_tokens={usage.prompt_tokens} · completion_tokens={usage.completion_tokens} "
                f"· {kept} chunks rode along, out of {total} in the collection\n", style=NUM)
    body.append("History keeps only (your message, this answer). The chunks are already gone.", style=TEXT_DIM)
    console.print(Panel(body, title="💬 4 · the response — and what persists",
                        border_style="bright_green", style=ON_BG, padding=(0, 1)))


def main() -> None:
    persist = os.environ.get("PERSIST_PATH")  # unset -> in memory, identical on every run
    col = create_collection(os.environ.get("COLLECTION", "knowledge"),
                            description="embeddings-rag-explorer demo",
                            metric="cosine", persist_path=persist)
    top_k = int(os.environ.get("TOP_K", "4"))
    threshold = float(os.environ.get("THRESHOLD", "0.4"))

    # --- INGESTION at startup: chunk knowledge.txt, insert through the manager ----
    text = open(os.path.join(os.path.dirname(__file__), "knowledge.txt")).read()
    pieces = chunk(text, CHUNK_SIZE, CHUNK_OVERLAP)
    stored = sum(insert(col, p, {"source": "knowledge.txt"})["ok"] for p in pieces)

    intro = Text()
    intro.append("Ingested ", style=TEXT)
    intro.append(f"{stored} chunks", style=NUM)
    intro.append(f" from knowledge.txt (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}) into the collection "
                 f"({col.count()} total, {'persisted' if persist else 'in memory'}).\n", style=TEXT)
    intro.append("Ask something; watch which chunks get chosen — and which get dropped. "
                 "Some questions to aim with:\n\n", style=TEXT)
    for i, s in enumerate(SUGGESTIONS, 1):
        intro.append(f"  {i}. ", style=NUM)
        intro.append(s + "\n", style=TEXT)
    intro.append("\n/topk N   /threshold X   (empty line = quit)", style=TEXT_DIM)
    console.print(Panel(intro, title="📚 Embeddings-RAG Explorer — simple dynamic RAG",
                        border_style="bright_magenta", style=ON_BG, padding=(1, 2)))

    history = []
    next_tip = 0
    while True:
        try:
            line = console.input("[bold bright_cyan]📝 you: [/bold bright_cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        if line.startswith("/topk"):
            top_k = int(line.split()[1]); console.print(Text(f"  top_k = {top_k}", style=NUM)); continue
        if line.startswith("/threshold"):
            threshold = float(line.split()[1]); console.print(Text(f"  threshold = {threshold}", style=NUM)); continue

        show_ui_send(history, line)

        # Retrieve WITHOUT the threshold first, so the dropped chunks are visible too.
        all_hits = query(col, line, top_k=top_k)
        kept = [h for h in all_hits if h["similarity"] >= threshold]
        dropped = [h for h in all_hits if h["similarity"] < threshold]
        show_retrieval(line, kept, dropped, top_k, threshold)
        if not kept:
            console.print(Text("  nothing passes the threshold — nothing to inject. "
                               "The model gets no context; lower /threshold to compare.\n", style=BAD))
            continue

        context = "\n\n".join(f"[{h['metadata'].get('source')} · chunk {h['metadata'].get('chunk_number')} "
                              f"· similarity {h['similarity']:.3f}]\n{h['chunk']}" for h in kept)
        augmented = TEMPLATE.format(context=context, user_input=line)
        messages = [{"role": "system", "content": SYSTEM}] + history + [{"role": "user", "content": augmented}]
        show_api_request(messages)

        resp = client.chat.completions.create(model=MODEL, messages=messages)
        answer = resp.choices[0].message.content
        show_response(answer, resp.usage, len(kept), col.count())

        history += [{"role": "user", "content": line},
                    {"role": "assistant", "content": answer}]

        # Keep the demo moving: hint the next suggestion the user hasn't tried.
        while next_tip < len(SUGGESTIONS) and SUGGESTIONS[next_tip].lower() in line.lower():
            next_tip += 1
        if next_tip < len(SUGGESTIONS):
            tip = SUGGESTIONS[next_tip]
            extra = "  (then /threshold 0.5 and ask again)" if tip.startswith("give me") else ""
            console.print(Text(f"💡 try: {tip}{extra}\n", style=TEXT_DIM))
            next_tip += 1

    console.print(Text("bye.", style=TEXT_DIM))


if __name__ == "__main__":
    main()
