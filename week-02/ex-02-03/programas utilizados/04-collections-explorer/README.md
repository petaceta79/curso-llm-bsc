<!-- =============================================================================================================== -->
<!-- Universitat Politècnica de Catalunya (UPC)                                                                      -->
<!-- =============================================================================================================== -->

# 🗂️ Collections Explorer

An embeddings database you can poke. A **collection** is a table indexed with
embeddings; this demo opens one — **persistent on disk by default**, so your chunks
are still there when you come back — and lets you fill it with chunks and basic
metadata, then search it by meaning.

Everything goes through the course's
[`collections-manager`](../../collections-manager/) utility (three functions:
`create_collection` / `insert` / `query`, on ChromaDB). That is also the point of
the demo: **your application talks to the abstraction layer, not to the engine
underneath.** For small-to-medium projects Chroma is more than enough — and if you
ever need a beefier store, you swap the layer's insides, not your application.

## Setup

```bash
cd collections-explorer
uv venv && source .venv/bin/activate && uv sync
```

Copy `.env.example` to `.env`. The default is local Ollama — no key, no cost:

```bash
ollama serve
ollama pull nomic-embed-text
```

## Run

```bash
uv run collections_explorer.py            # persistent collection at ./collections-store
uv run collections_explorer.py --memory   # throwaway in-memory collection
```

| Command | What it does |
|---|---|
| `/add <text>` | store a chunk (it asks for the **source**; the **chunk_number** within that source is auto-assigned) |
| `/seed` | load a few example chunks so queries land immediately |
| `/list` | everything in the collection: source · chunk_number · text |
| *(any other text)* | **query by meaning** — the nearest chunks, with their similarity and metadata |
| *(empty line)* | quit |

## The thing to notice

Add a few chunks, quit, and run it again: **they are still there** — that is the
database half of the story. Then query with words the chunks never use ("how quick
is the delivery robot?") and watch the right chunk surface anyway — that is the
embeddings half. Insert the same chunk twice and read the ko message: ids are
`source::chunk_number`, so a collection refuses silent duplicates.

## 📖 License

Licensed under [Creative Commons BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (`CC BY-NC-SA 4.0`).

## 👤 Author

[@granludo](https://github.com/granludo) — Marc Alier, Universitat Politècnica de Catalunya (UPC)
