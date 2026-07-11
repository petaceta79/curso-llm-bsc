# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

"""Simple dynamic RAG — the single-file cheat, with a database behind it.

Same shape as single-file RAG: a prompt template with {context} and {user_input},
bare turns in history, the model grounded on what we hand it. ONE thing changed —
where the context comes from. Instead of pasting a whole file every turn:

  1. take the {user_input} and use it as the QUERY,
  2. query the collection: the top-K chunks over the similarity threshold,
  3. format them (markdown, with their source metadata),
  4. insert that into the prompt template, ask, and answer.

The knowledge can now be as big as you want — fifty documents, a thousand — and
every turn still sends only a handful of relevant chunks. Ingest documents first
with ingest.py. Empty line to quit.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

from collections_manager import create_collection, query

load_dotenv()

client = OpenAI(
    base_url=os.environ.get("OPENAI_ENDPOINT", "http://localhost:11434/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "ollama"),
)
MODEL = os.environ.get("MODEL", "qwen3:1.7b")
TOP_K = int(os.environ.get("TOP_K", "4"))
THRESHOLD = float(os.environ.get("THRESHOLD", "0.4"))   # min cosine similarity

col = create_collection(os.environ.get("COLLECTION", "handbook"),
                        metric="cosine",
                        persist_path=os.environ.get("PERSIST_PATH", "./collections-store"))

SYSTEM = "Answer using only the context. If it is not there, say so."
TEMPLATE = "Context:\n----\n{context}\n----\n\nQuestion: {user_input}"


def format_context(hits: list[dict]) -> str:
    """Format the retrieved chunks as markdown, each with its provenance."""
    blocks = []
    for h in hits:
        m = h["metadata"]
        blocks.append(f"[{m['title']} · chunk {m['chunk_number']} · {m['md_url']} "
                      f"· similarity {h['similarity']:.3f}]\n{h['chunk']}")
    return "\n\n".join(blocks)


print(f"Simple dynamic RAG · model={MODEL} · collection={col.name} ({col.count()} chunks) "
      f"· top-{TOP_K} over {THRESHOLD}")
print("Ask about the ingested documents. Empty line to quit.\n")

history = []  # BARE turns only — retrieved chunks are rebuilt each turn, never stored

while True:
    user_input = input("you> ").strip()
    if not user_input:
        break

    # Dynamic augmentation: the user input IS the query.
    hits = query(col, user_input, top_k=TOP_K, threshold=THRESHOLD)
    if not hits:
        print(f"bot> (nothing in the collection passes similarity {THRESHOLD} — "
              f"ingest more documents, or lower THRESHOLD)\n")
        continue

    augmented = TEMPLATE.format(context=format_context(hits), user_input=user_input)
    messages = [{"role": "system", "content": SYSTEM}] + history + [{"role": "user", "content": augmented}]

    resp = client.chat.completions.create(model=MODEL, messages=messages)
    answer = resp.choices[0].message.content
    print(f"bot> {answer}")
    retrieved = ", ".join(f"{h['metadata']['source']}::{h['metadata']['chunk_number']}"
                          f"({h['similarity']:.2f})" for h in hits)
    print(f"     [retrieved {retrieved}]")
    print(f"     [{resp.usage.prompt_tokens} prompt tokens — {len(hits)} chunks rode along, "
          f"out of {col.count()} in the collection]\n")

    history += [{"role": "user", "content": user_input},
                {"role": "assistant", "content": answer}]
