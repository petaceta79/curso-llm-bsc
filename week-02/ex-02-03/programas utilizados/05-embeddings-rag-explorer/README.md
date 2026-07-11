<!-- =============================================================================================================== -->
<!-- Universitat Politècnica de Catalunya (UPC)                                                                      -->
<!-- =============================================================================================================== -->

# 📚 Embeddings-RAG Explorer

**The dynamic-RAG demo.** One program shows the whole loop. At startup it **ingests**
`knowledge.txt` — chunks it with a sliding window and inserts every chunk into a
collection through the course's [`collections-manager`](../../collections-manager/)
(the manager embeds and indexes each one). Then, on every turn, you watch dynamic
RAG happen, panel by panel:

1. **What the chat UI sends** — the bare turns, nothing else.
2. **Retrieval** — your message becomes the query; the collection returns the nearest
   chunks with their similarity, and you see which pass the threshold (**→ injected**)
   and which get dropped (**✗ below threshold**).
3. **What we actually send to the LLM** — system + history + template(message, chunks).
4. **The response — and what persists** — the answer, the token bill, and the fact that
   the chunks are already gone.

Everything speaks the manager's three calls — `create_collection` / `insert` / `query` —
the same interface as the collections-explorer, the provided
[`simple-dynamic-rag`](../../simple-dynamic-rag/) tool, and your final project. That is
the point of an abstraction layer: nobody here talks to the database engine directly.

## Setup

```bash
cd 05-embeddings-rag-explorer
uv venv && source .venv/bin/activate && uv sync
```

Copy `.env.example` to `.env`. Default is local Ollama — no key, no cost:

```bash
ollama serve
ollama pull qwen3:1.7b
ollama pull nomic-embed-text
```

## Run

```bash
uv run embeddings_rag_explorer.py
```

The collection lives **in memory** and is rebuilt from `knowledge.txt` on every run,
so every demo take starts identical. Set `PERSIST_PATH` in `.env` to keep it instead.

The intro panel **suggests questions to aim with** — a demo-friendly ladder from
"retrieval by meaning" (words the text never uses) through cross-domain provenance
to the off-topic threshold lesson — and after each answer it hints the next one, so
you always know what the next question is trying to show.

| Command | What it does |
|---|---|
| `/topk N` | how many chunks to retrieve |
| `/threshold X` | the similarity gate — watch chunks flip between injected and dropped |
| *(any text)* | one full turn, all four panels |
| *(empty line)* | quit |

## The thing to notice

Ask **"how quick is the delivery robot?"** — words the document never uses — and the
right chunk tops the table anyway: retrieval is by meaning. Then ask something the
document does not cover and read the similarity column. Unrelated questions still score
around 0.40–0.50 on this embeddings model, while real answers sit around 0.50–0.70 —
the band is narrow. Play with `/threshold`: find where off-topic questions inject
nothing while real ones still eat; push it higher and watch legitimate questions starve
too. The gate is a design decision that needs calibrating against your model and your
corpus — and the grounded system prompt is the second line of defense when something
slips through.

## 📖 License

Licensed under [Creative Commons BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (`CC BY-NC-SA 4.0`).

## 👤 Author

[@granludo](https://github.com/granludo) — Marc Alier, Universitat Politècnica de Catalunya (UPC)
