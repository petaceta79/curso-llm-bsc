<!-- =============================================================================================================== -->
<!-- Universitat Politècnica de Catalunya (UPC)                                                                      -->
<!-- =============================================================================================================== -->

# 🔁 Simple Dynamic RAG

The single-file cheat, with a database behind it. Same prompt template as
`single-file-rag` — `{context}` and `{user_input}` — but the context is no longer a
whole pasted file: it is **the top-K chunks retrieved by meaning from a collection**,
fresh on every turn. The knowledge can now be fifty documents or a thousand; each
question still ships only a handful of relevant chunks.

Two programs, matching the two halves of the workflow:

## 1 · Ingestion — `ingest.py`

Ingestion is how a document gets into a collection, in four steps:

1. **Convert to markdown** — [markitdown](https://github.com/microsoft/markitdown)
   handles pdf, docx, pptx, html, txt... For *scanned* documents you would use an
   OCR model instead: mistral-ocr in the cloud, or deepseek-ocr running locally
   (mlx on Apple Silicon, CUDA on NVIDIA).
2. **Store the original + its markdown distillation** somewhere linkable — here
   `static/`, the same idea as `/static` in a FastAPI app — so every chunk can point
   back to its document by URL.
3. **Chunk** the markdown (`chunking.py`, no framework — chunking is a for-loop):
   - `chars` — a sliding window: `--size` characters with `--overlap` shared margin,
     so a fact split at a boundary survives whole in one chunk. Works on any text.
   - `sections` — split at the document's own headings (`--level 2` cuts at `##`).
     Each chunk carries its own title; sizes vary with the document.
4. **Insert** each chunk with its metadata: `doc_url`, `md_url`, `title`,
   `chunk_number`, `chunking_strategy`, `ingested_at`.

```bash
uv run ingest.py docs/acme-handbook.md --strategy sections
uv run ingest.py somepaper.pdf --strategy chars --size 800 --overlap 100
```

## 2 · Query — `simple_dynamic_rag.py`

Simple dynamic augmentation: take the `{user_input}` and use it **as the query**;
query the collection; keep the top-K chunks **over the similarity threshold**; format
them (markdown, provenance included); insert into the prompt template; answer.

```bash
uv run simple_dynamic_rag.py
```

## Setup

```bash
cd simple-dynamic-rag
uv venv && source .venv/bin/activate && uv sync
```

Copy `.env.example` to `.env`. Default is local Ollama — no key, no cost:

```bash
ollama serve
ollama pull qwen3:1.7b
ollama pull nomic-embed-text
```

Built on the course's [`collections-manager`](../collections-manager/) utility —
the application talks to the abstraction layer, not to the engine underneath.

## The thing to notice

Ingest the handbook, then ask **"how quick is the delivery robot?"** — the words
don't appear in any chunk, and the right section surfaces anyway. Watch the
`prompt_tokens` line: only the retrieved chunks ride along, however big the
collection grows.

Then ask for a noodle recipe and look at the similarities. Surprise: completely
unrelated questions still score around 0.40–0.50 on this embeddings model, while
real answers sit around 0.50–0.70 — the band is narrow, so a threshold needs
calibrating against *your* model and corpus, and it will not catch everything.
That is why the grounded system prompt ("answer only from the context") is the
second line of defense: even when a barely-related chunk slips through the gate,
the model still refuses to invent a recipe from it. Raise `THRESHOLD` and watch
the gate tighten — and notice when it starts starving legitimate questions too.

## 📖 License

Licensed under [Creative Commons BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (`CC BY-NC-SA 4.0`).

## 👤 Author

[@granludo](https://github.com/granludo) — Marc Alier, Universitat Politècnica de Catalunya (UPC)
