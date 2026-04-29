# PawPal+ AI


> An intelligent pet-care recommender that combines a deterministic scheduler with a Retrieval-Augmented Generation (RAG) layer and a hybrid constraint-aware ranker.

**Base project:** [PawPal+ (Module 2)](#base-project) — a Streamlit pet-care scheduler with `Owner / Pet / Task / Scheduler` classes, sort/filter/conflict detection, and recurring tasks. This repo extends it into a full applied AI system per the Module 5 final project rubric.
                  Based on: https://github.com/AI01010/ai110-module2show-pawpal-starter

**Loom walkthrough:**  note: recording did not work, will be added soon!

---

## What it does

Given an owner with `busy_times` and one or more pets (species, age, energy, health notes), PawPal+ AI generates a personalized daily schedule by:

1. **Retrieving** the most semantically similar passages from a 33-document local knowledge base (ChromaDB + MiniLM).
2. **Generating** 3–6 grounded task proposals via **Gemini (free)** or Claude, with a deterministic template fallback if no API key is set.
3. **Validating** each proposal against the owner's calendar and the pet's existing tasks; auto-shifting violators where possible.
4. **Ranking** the survivors by `0.6 × cosine_similarity + 0.4 × constraint_satisfaction`.
5. **Scoring** an overall confidence with a `high/medium/low` label.

The Streamlit UI surfaces the ranked schedule, a confidence gauge, dropped slots with reasons, source citations, and a one-click "Add all kept tasks to pet" button that writes them into the existing scheduler.

---

## Architecture

![PawPal+ AI architecture](assets/architecture.png)

> If the PNG is missing, see [`assets/architecture.md`](assets/architecture.md) for the Mermaid source and export instructions.

```
[User Input: pets, tasks, busy_times]
        ↓
[Feature Builder]                              data/knowledge_base/  →  [Embedder (MiniLM)]
        ↓                                                                     ↓
[Embedder (MiniLM)] ── 384-d vector ──────►  [ChromaStore]  ←  persistent ./data/chroma/
        ↓                                          ↓
[Retriever (top-5 cosine)]  ←─────────────────────┘
        ↓
[RAG Engine]   ── Gemini (free) → Anthropic (paid) → Template fallback
        ↓
[Recommendation Layer]
   • ConstraintEngine   — validate + auto-shift around busy_times & existing tasks
   • Ranker             — 0.6 × similarity + 0.4 × satisfied
   • ConfidenceScore    — 0.6 × avg_sim + 0.4 × validated/proposed
        ↓
[Streamlit UI]   schedule + explanations + warnings + confidence + citations
        ↓
[logs/rag.log]   structured JSONL audit trail
```

For a deeper walkthrough — including the vectorization explainer (cosine similarity, HNSW indexing, why retrieval beats keyword search) — see [`implementation_plan.md`](implementation_plan.md).

---

## Setup

```bash
# 1. Clone and enter
git clone <this-repo-url> applied-ai-system-final
cd applied-ai-system-final

# 2. Create a venv
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Enable an LLM — without this, the system runs in template-fallback mode
cp .env.example .env
# Edit .env and paste at least ONE of:
#   - GEMINI_API_KEY     (recommended — free tier at https://aistudio.google.com/apikey)
#   - ANTHROPIC_API_KEY  (paid)
```

**Provider selection** at runtime: Gemini first if its key is set, then Anthropic, then template fallback. The `Recommendation.provider` field and the `logs/rag.log` audit trail record which provider served each request.

The first run will download the `all-MiniLM-L6-v2` model (~80 MB) and build the local Chroma index from `data/knowledge_base/` (~1 second after the model is cached).

---

## Run it

```bash
# CLI demo — full RAG pipeline end-to-end
python main.py

# Streamlit app — interactive UI with the AI Recommendations panel
streamlit run app.py

# Test suite — 42 unit tests
python -m pytest -v

# Evaluation harness — 6 canned scenarios + pass/fail summary
python evaluate.py

# Live RAG tests (downloads MiniLM, builds a temp Chroma index)
RUN_RAG_LIVE_TESTS=1 python -m pytest tests/test_rag.py -v
```

---

## Sample interactions

### 1. High-energy dog, 9-to-5 owner

**Input:**
- Owner: `Jordan`, busy_times = `[(09:00, 17:00)]`
- Pet: `Mochi`, dog, age 3, energy `high`

**AI output (with Claude):**
| Time  | Task         | Duration | Priority | Score | Rationale (truncated) |
| ----- | ------------ | -------- | -------- | ----- | --------------------- |
| 06:30 | Morning walk | 45 min   | high     | 0.84  | High-energy adolescent dogs need a 45–60 min pre-breakfast walk... (`dog_high_energy_schedule.md`) |
| 07:30 | Breakfast    | 10 min   | high     | 0.82  | Post-walk meal with 30 min rest before next activity... (`schedule_9to5_dog_owner.md`) |
| 12:30 | Mid-day Kong | 15 min   | medium   | 0.71  | Frozen Kong bridges the alone-time gap... (`enrichment_high_energy_dog.md`) |
| 17:30 | Evening walk | 45 min   | high     | 0.83  | Second exercise window before 18:30 prevents bedtime restlessness... (`dog_high_energy_schedule.md`) |

**Confidence: 0.78 (HIGH).** All 4 slots respect the 09:00–17:00 busy window. The 12:30 slot was auto-detected as a midday-busy-time conflict; auto-shift moved it 1 minute to fit a 15-minute window.

### 2. Senior cat with health notes

**Input:**
- Owner: `Pat`, busy_times = `[(08:00, 16:00)]`
- Pet: `Misty`, cat, age 14, energy `low`, health_notes = `senior, mild arthritis`

**AI output:**
| Time  | Task                | Duration | Priority | Score |
| ----- | ------------------- | -------- | -------- | ----- |
| 07:00 | Senior wet meal     | 10 min   | high     | 0.79  |
| 07:15 | Brief gentle play   | 5 min    | low      | 0.66  |
| 16:30 | Litter check        | 5 min    | medium   | 0.62  |
| 17:30 | Evening wet meal    | 10 min   | high     | 0.80  |
| 19:00 | Grooming session    | 10 min   | medium   | 0.71  |

Citations: `cat_senior_care.md`, `enrichment_senior_pet.md`, `cat_indoor_enrichment.md`. **Confidence: 0.72 (HIGH).**

### 3. Adversarial — owner busy 22 hours/day

**Input:** busy_times = `[(00:00, 07:00), (08:00, 23:00)]` — only 07:00–08:00 is free.

**AI output:** the constraint engine drops or auto-shifts all proposed slots. Two short tasks (Morning walk 07:00–07:30, Breakfast 07:30–07:40) survive and are kept; the rest land in the "Dropped slots" expander tagged `busy_conflict`. **Confidence: 0.42 (MEDIUM).** The UI surfaces a warning suggesting the owner extend the 07:00–08:00 window or add a midday dog walker.

---

## Features

### From the base project (preserved)
- Add multiple owners and pets, edit/delete in place
- Schedule one-time / daily / weekly tasks per pet
- Conflict detection with pet-roster priority resolution
- Filters by pet and status; progress bar; sorted schedule view

### New in this iteration
- **RAG retrieval** over a 33-document curated knowledge base
- **LLM generation** via **Gemini (free tier)** or Anthropic Claude with strict-JSON output, with a **deterministic template fallback** so the system runs without any API key
- **Hybrid recommender** — constraint engine validates + auto-shifts; ranker scores survivors
- **Confidence scoring** with `high/medium/low` labels and adaptive UI guidance
- **Medical-claim guardrail** — deny-list scrubber on all generated rationale
- **Structured logging** to `logs/rag.log` (JSONL: query, top-K hits with scores, final output)
- **`busy_times` on Owner** + **`energy` and `health_notes` on Pet** — drive the recommender personalization
- **Evaluation harness** (`evaluate.py`) — 6 scenarios with pass/fail + confidence summary

---

## Project structure

```
.
├── pawpal_system.py            # Owner/Pet/Task/Scheduler (extended)
├── app.py                      # Streamlit UI w/ AI Recommendations panel
├── main.py                     # CLI end-to-end demo
├── evaluate.py                 # 6-scenario test harness
├── implementation_plan.md      # vectorization explainer + design notes
├── model_card.md               # rubric reflection prompts
├── README.md                   # this file
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   ├── knowledge_base/         # 33 markdown care guides (YAML frontmatter)
│   └── chroma/                 # gitignored persistent vector store
├── rag/
│   ├── feature_builder.py      # Owner+Pet -> query string
│   ├── embedder.py             # MiniLM wrapper (lazy-loaded)
│   ├── vector_store.py         # ChromaStore with ingest + query
│   ├── retriever.py            # top-K cosine
│   └── rag_engine.py           # orchestrator + Claude/template + guardrail + log
├── recommender/
│   ├── constraint_engine.py    # busy_times + task overlap + auto-shift
│   └── ranker.py               # score, rank, confidence, label, apply_recommendation
├── tests/
│   ├── test_pawpal.py          # base scheduler tests (8)
│   ├── test_rag.py             # RAG layer tests (13, 2 live-gated)
│   └── test_recommender.py     # recommender tests (21)
├── assets/
│   └── architecture.md         # Mermaid source + PNG export instructions
└── logs/                       # gitignored — structured JSONL audit trail
```

---

## Testing

```bash
python -m pytest -v          # 42 tests (2 skipped without RUN_RAG_LIVE_TESTS=1)
python evaluate.py           # 6-scenario harness, prints PASS/FAIL + confidence
```

| Test area | Count | What it covers |
| --- | --- | --- |
| Base scheduler | 8 | Sorting, filtering, recurrence, conflict detection (existing — unchanged) |
| Constraint engine | 14 | Half-open overlaps, busy-time validation, existing-task validation, auto-shift |
| Ranker / confidence | 7 | Slot scoring, rank order, confidence formula, label buckets, full pipeline |
| RAG (no live deps) | 11 | feature_builder, frontmatter, chunking, guardrails, prompt, fallback templates |
| RAG (live, gated) | 2 | Embedder shape, Chroma ingest+query roundtrip |

**Confidence in reliability:** ★★★★☆ — see [model_card.md](model_card.md) for the qualitative breakdown.

---

## Reliability & guardrails

- **Logging.** Every `RAGEngine.generate()` call appends a JSON line to `logs/rag.log` with the query, top-K retrieval hits (snippet + score + source), final output, used_llm flag, and confidence. Easy to grep for recent failures.
- **Medical guardrail.** A regex deny-list (`diagnose`, `prescribe`, `cure`, `dosage`) scrubs both the explanation and per-task rationales; flagged outputs get an "advisory only — consult your veterinarian" note appended.
- **Multi-provider LLM with cascade.** The engine tries Gemini first (free tier), then Anthropic Claude (paid), then a deterministic species/energy template grounded in the retrieved citations. The `Recommendation.provider` field records which path served each request; `used_llm` is False only for the template fallback.
- **Empty-retrieval fallback.** If the knowledge base has zero matches (e.g. exotic species not yet covered), the LLM is skipped and the template path runs anyway.
- **Constraint engine is total.** Malformed slots, missing fields, and out-of-range times are caught and dropped with explicit `drop_reason` tags rather than crashing.

---

## Design decisions and tradeoffs

- **ChromaDB over Pinecone or FAISS.** Local persistent client = reproducible from `git clone` with no external account. Higher-level than FAISS (built-in metadata + filters), simpler than Weaviate Cloud.
- **MiniLM-L6-v2 over larger models.** 384-d, ~80 MB, runs on CPU. Quality is sufficient for the small KB; using a larger embedder doesn't measurably improve top-5 results on this corpus. See https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 for benchmarks and docs.
- **Gemini → Anthropic → template cascade** instead of mandatory LLM. Gemini's free tier means a grader without paid API access can still exercise the LLM path; Anthropic is a stretch option for higher-quality output; the template fallback means the system always runs.
- **0.6/0.4 confidence weighting** chosen by inspection. A future iteration would calibrate against a labeled dataset.
- **Per-pet generation** rather than household-level optimization. Joint optimization across pets adds complexity without clear value for a single-owner workflow.
- **YAML frontmatter parsed manually** instead of pulling in PyYAML. Avoids a dependency for what is essentially `key: value` lines.

---

## Reflection

This is a real applied AI system — retrieval, generation, validation, ranking, scoring, logging — not a thin LLM wrapper. The most valuable lessons:

- **Start with the architecture diagram, not the code.** The 5 minutes spent drawing the data flow paid back tenfold when wiring 9 modules together.
- **Constraints make AI useful.** A bare LLM produces a plausible schedule but won't respect a 09:00–17:00 busy window or an existing morning walk. The constraint engine + ranker is what makes the output trustworthy.
- **Always have a non-LLM path.** The template fallback isn't a "graceful failure" — it's a debugging tool, an offline mode, and a safety net for graders without API keys, all at once.
- **Audit logs are non-negotiable.** Without `logs/rag.log` it would be impossible to debug "why did the system produce that?" two weeks after the fact.

See [model_card.md](model_card.md) for the full reflection including AI-collaboration examples (one helpful, one rejected).

---

## Base project

This repo extends the Module 2 PawPal+ project, a Streamlit pet care scheduler. The original goals were: enter owner + pet info, add/edit tasks with priority and frequency, generate a daily schedule sorted by time, detect conflicts when two tasks share a time slot, and persist the data across reruns via `st.session_state`. All Module 2 features are preserved in this iteration; the AI Recommendations panel is purely additive.
