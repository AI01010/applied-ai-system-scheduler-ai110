"""End-to-end CLI demo: ingest knowledge base -> retrieve -> generate -> validate -> print.

Run: python main.py

This script exercises the full RAG pipeline. It works without an Anthropic API key
(falls back to the deterministic template) and without a pre-built vector store
(builds it from data/knowledge_base/ on first run, then reuses).
"""

from pawpal_system import Owner, Pet, Task, Scheduler


def section(title: str) -> None:
    bar = "=" * 60
    print(f"\n{bar}\n  {title}\n{bar}")


def main() -> None:
    # ── 1. Build the household ────────────────────────────────────────────────
    section("1. Household setup")
    owner = Owner(
        name="Jordan",
        contact_info="jordan@email.com",
        busy_times=[("09:00", "17:00")],
    )

    mochi = Pet(name="Mochi", species="dog", age=3, energy="high",   health_notes="")
    luna  = Pet(name="Luna",  species="cat", age=11, energy="low",   health_notes="senior, mild arthritis")
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # Pre-existing tasks the AI must respect when validating its own proposals.
    mochi.add_task(Task(title="Morning walk", time="07:30", duration_minutes=30, priority="high", frequency="daily"))
    luna.add_task( Task(title="Feeding",      time="07:00", duration_minutes=10, priority="high", frequency="daily"))

    print(f"Owner: {owner.name}, busy {owner.busy_times}")
    print(f"Pets:  {[(p.name, p.species, p.energy, p.age) for p in owner.pets]}")

    # ── 2. Existing rule-based schedule (the Module 2 layer) ──────────────────
    section("2. Existing rule-based schedule (no AI)")
    scheduler = Scheduler(owner)
    for t, pn in scheduler.get_tasks_with_pets():
        status = "[done]" if t.completed else "[    ]"
        print(f"  {status} {t.time}  {t.title:<20} ({pn}) — {t.frequency}")

    # ── 3. RAG pipeline ───────────────────────────────────────────────────────
    section("3. RAG pipeline — ingest -> retrieve -> generate")

    try:
        from rag.rag_engine import RAGEngine
        from rag.vector_store import ChromaStore
        from recommender.ranker import apply_recommendation
    except ImportError as e:
        print(f"\n[ERROR] RAG dependencies not installed: {e}")
        print("Run: pip install -r requirements.txt")
        return

    print("Building local Chroma index from data/knowledge_base/...")
    store = ChromaStore()
    chunk_count = store.ingest_knowledge_base()
    print(f"Index ready: {chunk_count} chunks in collection '{store.COLLECTION_NAME}'.")

    engine = RAGEngine(store=store)

    for pet in owner.pets:
        section(f"4. AI recommendations for {pet.name} the {pet.species}")
        rec = engine.generate(owner, pet, k=5)

        print(f"  provider:       {rec.provider}  (used_llm={rec.used_llm})")
        print(f"  retrieval avg:  {rec.confidence:.3f}")
        print(f"  citations:      {rec.citations[:3]}{'...' if len(rec.citations) > 3 else ''}")
        print(f"  explanation:    {rec.explanation[:100]}{'...' if len(rec.explanation) > 100 else ''}")

        # Recommender layer — validate against owner.busy_times + existing tasks
        result = apply_recommendation(
            rec,
            busy_times=owner.busy_times,
            existing_tasks=pet.tasks,
        )

        print(f"\n  Confidence: {result['confidence']:.2f} ({result['confidence_label'].upper()})")
        print(f"  Kept: {len(result['kept'])}  Dropped: {len(result['dropped'])}")

        print("\n  Ranked schedule:")
        for s in result["ranked"]:
            shifted = "*" if s.get("shifted") else " "
            print(f"   {shifted} {s.get('time', '?')}  {s.get('title', '?'):<22} "
                  f"score={s.get('score', 0):.2f}  ({s.get('priority', 'medium')})")

        if result["dropped"]:
            print("\n  Dropped (constraint violations):")
            for d in result["dropped"]:
                print(f"    - {d.get('time', '?')}  {d.get('title', '?'):<22} reason={d.get('drop_reason', '?')}")

    # ── 5. Top retrieval hits for inspection ──────────────────────────────────
    section("5. Top retrieval hits for Mochi (debug view)")
    from rag.feature_builder import build_query
    q = build_query(owner, mochi)
    print(f"Query:\n  {q}\n")
    for i, hit in enumerate(store.query(q, k=5), start=1):
        print(f"  [{i}] score={hit['score']:.3f}  source={hit['source']}")
        print(f"      {hit['text'][:140].strip()}...")
    print()


if __name__ == "__main__":
    main()
