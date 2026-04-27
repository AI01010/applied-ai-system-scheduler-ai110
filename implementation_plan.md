# PawPal+ AI — Implementation Plan

This file is the in-repo companion to the architectural plan. It explains **what we're building, how the AI parts work, and why we made the choices we did** — written so a future employer reading the GitHub portfolio can follow the reasoning end-to-end.

The base project (Module 2 PawPal+) is a Streamlit pet-care scheduler with `Owner / Pet / Task / Scheduler` classes. This extension transforms it into a **Retrieval-Augmented Generation (RAG) system with a hybrid recommender**.

---

## 1. Why RAG (and why ChromaDB locally)

**RAG = Retrieve, then Generate.** Instead of asking an LLM "make a schedule for my dog" and hoping its training data was relevant, we first **retrieve** the most relevant passages from a curated knowledge base, then ask the LLM to generate the schedule **using those passages as grounding context**. This:

- Reduces hallucination — the model has real care guidance in its prompt.
- Lets us update knowledge without retraining — just add a markdown file.
- Gives us auditability — we log which documents drove each recommendation.

### Why ChromaDB is a "local" vector DB

ChromaDB ships two modes:

| Mode | What it does |
| --- | --- |
| `chromadb.Client()` | In-memory only; data dies with the Python process. Good for tests. |
| `chromadb.PersistentClient(path="./data/chroma/")` | **What we use.** Writes a SQLite + parquet store to disk. Survives restarts. No server, no cloud, no API key. |

Compare to alternatives:

- **Pinecone, Weaviate Cloud** — managed services, need an API key and network access.
- **FAISS** — local but lower-level (you manage IDs, metadata, persistence yourself).
- **ChromaDB persistent** — local *and* high-level (filters, metadata, collections built-in).

Our entire AI stack runs offline-first. The only optional cloud call is the LLM (Anthropic Claude); if no API key is set, the system falls back to a deterministic template that still uses retrieved context.

---

## 2. How vectorization works (the AI-engineering 101 walkthrough)

A **vector** (or **embedding**) is a fixed-length list of floating-point numbers that represents the *meaning* of a piece of text. We use `sentence-transformers/all-MiniLM-L6-v2`, which produces **384-dimensional** vectors. The model has been trained so that **two texts with similar meaning produce vectors pointing in similar directions** — even if they share no words.

### The 5 stages of our RAG pipeline

```
[markdown docs]                    [user query]
      │                                 │
      ▼                                 ▼
  ┌────────────┐                  ┌────────────┐
  │ 1. Chunk   │                  │ 1. Build   │
  │ ~200 tokens│                  │ from pet   │
  └─────┬──────┘                  │ + owner    │
        │                         └─────┬──────┘
        ▼                               │
  ┌────────────┐                        │
  │ 2. Embed   │  same model as ───────►│ 2. Embed
  │ MiniLM     │  query side            │ MiniLM
  └─────┬──────┘                        │
        ▼                               ▼
  ┌────────────────────┐         ┌────────────┐
  │ 3. Index in Chroma │ ──────► │ 4. Cosine  │
  │ (HNSW graph)       │         │ top-K=5    │
  └────────────────────┘         └─────┬──────┘
                                       ▼
                                 ┌────────────┐
                                 │ 5. Augment │
                                 │ LLM prompt │
                                 └────────────┘
```

**Stage details:**

1. **Chunking** — Markdown files in `data/knowledge_base/` are split into ~200-token passages. Smaller than this and chunks lose context; bigger than this and the embedding becomes a blurry average of unrelated topics.

2. **Embedding** — Each chunk goes through MiniLM, producing a 384-d vector. *The same model encodes the user's query at search time*, which is the critical invariant: if you embed the corpus with model A and queries with model B, the vectors live in different spaces and similarity is meaningless.

3. **Indexing** — Vectors + their original text + metadata (`pet_type`, `topic`, `source`) are stored in a Chroma collection. Chroma builds an **HNSW (Hierarchical Navigable Small World)** graph index for sublinear-time nearest-neighbor lookup. Naive linear scan would be O(n); HNSW is roughly O(log n).

4. **Retrieval** — At query time, we embed the user's question, then ask Chroma for the top-K (K=5) most similar chunks by **cosine similarity**:

   ```
   cos_sim(a, b) = (a · b) / (‖a‖ · ‖b‖)
   ```

   Range is `[-1, 1]`. We treat scores ≥ 0.5 as confidently relevant. Cosine is preferred over Euclidean here because we care about *direction* (meaning) not *magnitude* (text length).

5. **Augmentation** — The retrieved chunks are concatenated into the LLM prompt as a `<context>` block. The LLM is instructed to **only use facts from the context** when generating recommendations. We also attach per-chunk citations so we can log "this advice came from `cat_high_energy.md`."

### Why this beats keyword search

Query: *"my hyper puppy is restless every afternoon"*

- **Keyword search** — looks for "hyper", "puppy", "restless", "afternoon" — misses a doc titled "Adolescent dogs need a second exercise window" because no words overlap.
- **Vector search** — both texts get embedded into the same semantic space; their vectors point the same way; the doc is retrieved at rank #1.

This is the entire point of dense embeddings: **semantic similarity, not lexical similarity.**

---

## 3. The hybrid recommender layer

Retrieval alone isn't a recommender — it just finds relevant text. We layer three more components on top:

### a. Content-based filtering
Pet attributes (`species`, `age`, `energy`, `health_notes`) are folded into the query string by `feature_builder.build_query()`. This biases retrieval toward chunks tagged with matching `pet_type` and `topic` metadata.

### b. Constraint engine (`recommender/constraint_engine.py`)
Validates each proposed time slot against:
- `Owner.busy_times` (e.g. `[("09:00", "17:00")]`)
- Existing tasks (no overlap)
- Pet-specific limits (no walks within 1h of feeding for some species)

Slots that fail are **dropped or auto-shifted** to the nearest valid window.

### c. Ranker + confidence (`recommender/ranker.py`)
Final ordering uses:

```
score = 0.6 × cosine_similarity + 0.4 × constraint_satisfaction
```

System-level **confidence**:

```
confidence = 0.6 × avg(top-K similarity)
           + 0.4 × (validated_slots / proposed_slots)
```

| Confidence | Meaning |
| --- | --- |
| ≥ 0.7 | High — surface as "AI recommends" |
| 0.4–0.7 | Medium — surface with "consider" wording |
| < 0.4 | Low — fall back to rule-based scheduler + warning |

---

## 4. Module layout

```
applied-ai-system-final/
├── pawpal_system.py            # base Owner/Pet/Task/Scheduler (Module 2)
├── app.py                      # Streamlit UI (extended w/ AI panel)
├── main.py                     # CLI demo (extended w/ RAG flow)
├── evaluate.py                 # NEW — test harness across 5+ scenarios
├── implementation_plan.md      # ← this file
├── model_card.md               # NEW — rubric reflection
├── README.md                   # extended
├── requirements.txt            # extended
├── .env.example                # NEW
├── .gitignore                  # NEW
├── data/
│   ├── knowledge_base/         # NEW — ~40 markdown care guides
│   └── chroma/                 # NEW — gitignored persistent vector store
├── rag/                        # NEW
│   ├── __init__.py
│   ├── feature_builder.py
│   ├── embedder.py
│   ├── vector_store.py
│   ├── retriever.py
│   └── rag_engine.py
├── recommender/                # NEW
│   ├── __init__.py
│   ├── constraint_engine.py
│   └── ranker.py
├── tests/
│   ├── test_pawpal.py          # existing — kept as-is
│   ├── test_rag.py             # NEW
│   └── test_recommender.py     # NEW
├── assets/
│   └── architecture.md         # NEW — Mermaid source
└── logs/
    └── rag.log                 # NEW — structured JSONL audit log
```

---

## 5. AI feature → rubric mapping

The assignment requires at least one of: RAG, agentic workflow, fine-tuned model, or reliability/testing system. We do **two**:

| Feature | Where |
| --- | --- |
| **RAG (required)** | `rag/` module — fully integrated, LLM output is grounded on retrieved chunks |
| **Reliability/testing (stretch)** | `evaluate.py` — test harness that scores 5+ canned scenarios end-to-end |

Plus the rubric-required:

- **Logging** — `logs/rag.log` captures query, top-K hits, final output, rejected slots
- **Guardrails** — medical-advice deny-list, "advisory only" disclaimer, fallback to rule-based when retrieval is empty
- **Confidence scoring** — formula above, displayed in UI

---

## 6. Run / verify

```bash
pip install -r requirements.txt
python main.py            # CLI: ingests KB, runs full RAG pipeline, prints schedule
python -m pytest -v       # 8 base tests + new RAG/recommender tests
python evaluate.py        # prints pass/fail + confidence per scenario
streamlit run app.py      # UI smoke test
```

**Optional but recommended:** set `ANTHROPIC_API_KEY` in `.env` for the full LLM experience. Without it, the system runs in deterministic-template mode (still uses retrieval, just skips the LLM call).
