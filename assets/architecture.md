# PawPal+ AI — System Architecture

This file is the source of truth for the system diagram. Render it with the [Mermaid Live Editor](https://mermaid.live), then export `architecture.png` into this folder for the README. Free Mermaid accounts cap at 3 stored charts; the Live Editor has no such limit.

## Mermaid source

```mermaid
flowchart TD
    subgraph UI["Streamlit UI (app.py)"]
        OWNER_FORM[Owner Setup<br/>name, contact, busy_times]
        PET_FORM[Pet Form<br/>species, age, energy, health_notes]
        AI_PANEL[AI Recommendations Panel<br/>generate button + confidence gauge]
    end

    subgraph CORE["Core Domain (pawpal_system.py)"]
        OWNER[Owner]
        PET[Pet]
        TASK[Task]
        SCHED[Scheduler<br/>sort/filter/conflict]
    end

    subgraph RAG["RAG Layer (rag/)"]
        FB[feature_builder<br/>Owner+Pet -> query string]
        EMB[Embedder<br/>MiniLM 384-d]
        VS[ChromaStore<br/>persistent local]
        RET[Retriever<br/>top-K cosine]
        ENG[RAGEngine<br/>Claude OR template]
        LOG[(logs/rag.log<br/>JSONL audit)]
    end

    subgraph KB["Knowledge Base"]
        DOCS[33 markdown docs<br/>data/knowledge_base/]
    end

    subgraph REC["Recommender Layer (recommender/)"]
        CE[ConstraintEngine<br/>busy_times + existing tasks<br/>auto-shift]
        RANK[Ranker<br/>0.6*sim + 0.4*satisfied]
        CONF[ConfidenceScore<br/>+ label]
    end

    subgraph EVAL["Reliability"]
        TESTS[42 unit tests<br/>tests/]
        HARNESS[evaluate.py<br/>6 scenarios]
    end

    OWNER_FORM --> OWNER
    PET_FORM --> PET
    OWNER --> PET
    PET --> TASK
    OWNER --> SCHED

    AI_PANEL --> FB
    OWNER --> FB
    PET --> FB
    FB --> EMB
    DOCS --> VS
    EMB --> VS
    VS --> RET
    RET --> ENG
    ENG --> LOG
    ENG --> CE
    OWNER -.busy_times.-> CE
    PET -.tasks.-> CE
    CE --> RANK
    RANK --> CONF
    CONF --> AI_PANEL

    TESTS -.exercise.-> CE
    TESTS -.exercise.-> RANK
    HARNESS -.exercise.-> ENG

    classDef ui     fill:#e1f5fe,stroke:#0277bd,color:#01579b;
    classDef core   fill:#f3e5f5,stroke:#7b1fa2,color:#4a148c;
    classDef rag    fill:#e8f5e9,stroke:#388e3c,color:#1b5e20;
    classDef rec    fill:#fff3e0,stroke:#f57c00,color:#e65100;
    classDef kb     fill:#fce4ec,stroke:#c2185b,color:#880e4f;
    classDef eval   fill:#ede7f6,stroke:#5e35b1,color:#311b92;
    classDef store  fill:#fafafa,stroke:#616161,color:#212121,stroke-dasharray:5 5;

    class OWNER_FORM,PET_FORM,AI_PANEL ui;
    class OWNER,PET,TASK,SCHED core;
    class FB,EMB,VS,RET,ENG rag;
    class CE,RANK,CONF rec;
    class DOCS kb;
    class TESTS,HARNESS eval;
    class LOG store;
```

## Data flow narrative

1. The user fills the **Owner Setup** form (`name`, `contact`, `busy_times`) and adds **Pets** (`species`, `age`, `energy`, `health_notes`).
2. Clicking "Generate AI schedule" calls `feature_builder.build_query(owner, pet)` which produces a natural-language query embedding the relevant signals.
3. On first run, `ChromaStore.ingest_knowledge_base()` loads all 33 markdown files, parses YAML frontmatter, chunks each by paragraph (≤1000 chars), embeds them with MiniLM, and upserts into a persistent local Chroma collection at `./data/chroma/`.
4. `Retriever.top_k()` returns the 5 most-similar chunks via cosine similarity.
5. `RAGEngine.generate()` either:
   - Calls Anthropic Claude with the chunks as `<context>` and parses a strict-JSON response containing `proposed_tasks`, `explanation`, `citations`, OR
   - Falls back to a deterministic species/energy template if no API key is set or the LLM call fails.
6. The medical-claim guardrail scrubs any rationale that looks like medical advice and appends an "advisory only" warning.
7. `recommender.constraint_engine.validate_slots()` partitions the proposed slots into `kept` and `dropped`, auto-shifting violators to the next valid 15-minute window.
8. `recommender.ranker.rank_slots()` orders the survivors by `0.6 × avg_similarity + 0.4 × satisfied`.
9. `recommender.ranker.confidence_score()` produces the final `[0,1]` confidence and bucketed `high/medium/low` label.
10. The Streamlit AI Recommendations panel renders the schedule table, dropped-slot inspector, citations, and confidence gauge — and offers a one-click "Add all kept tasks to pet" button that writes them into the existing Scheduler.
11. Every generation is appended as a JSON line to `logs/rag.log` for auditability.

## To export PNG for the README

1. Open the Mermaid block above in [mermaid.live](https://mermaid.live).
2. Use **Actions -> Download PNG** (or copy the URL of the PNG export).
3. Save as `assets/architecture.png` next to this file.
4. The README references it as `![architecture](assets/architecture.png)`.
