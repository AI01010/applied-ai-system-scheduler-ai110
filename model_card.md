# PawPal+ AI — Model Card

This file answers the rubric reflection prompts: what the system does, who it's for, what its limitations are, how it was tested, how it could be misused, and how I collaborated with AI to build it.

## Project identification

- **Base project:** PawPal+ (Module 2 — pet care scheduler with `Owner`, `Pet`, `Task`, `Scheduler` classes and Streamlit UI).
- **This iteration:** Module 5 final — Applied AI System extension. Adds a RAG layer (ChromaDB + sentence-transformers + optional Claude) and a hybrid recommender (constraint engine + ranker + confidence scoring) on top of the existing scheduler.
- **Intended use:** advisory schedule recommendations for individual pet owners. Not a medical tool, not a replacement for veterinary care.

## What the AI does

Given an `Owner` (with `busy_times`) and a target `Pet` (species, age, energy, health notes), the system:

1. Retrieves the 5 most semantically similar passages from a curated 33-document knowledge base.
2. Asks Claude to propose 3–6 daily care tasks grounded in those passages, OR falls back to a deterministic species/energy template if no API key is set.
3. Validates each proposed slot against the owner's busy windows and existing tasks; auto-shifts violators where possible.
4. Ranks the survivors by `0.6 × cosine_similarity + 0.4 × constraint_satisfaction` and emits a `[0,1]` confidence with a `high/medium/low` label.
5. Logs every generation as a JSON line to `logs/rag.log`.

## Limitations and biases

- **Knowledge-base bias.** The 33 seed documents reflect mainstream Western pet-keeping conventions (typical dog breeds, indoor cats, common pet species). They under-represent: working farm dogs, exotic pets beyond rabbits/birds, regional husbandry practices, and pets with rare medical conditions.
- **Embedding model bias.** `all-MiniLM-L6-v2` is trained primarily on English data. Queries in other languages will retrieve poorly.
- **Conflict-detection simplicity.** The constraint engine treats slots as discrete intervals. It does not yet model "wind-down windows" or "quiet hours" — a 21:00 walk that ends at 21:30 is technically valid but behaviorally suboptimal.
- **Schedule personalization is shallow.** The system uses species, age, energy, and health notes as features. It does not yet learn from the owner's *acceptance* or *rejection* of past recommendations — there is no preference-learning loop.
- **Confidence is heuristic.** The `0.6/0.4` weighting was chosen by inspection, not calibrated against a labeled dataset. A "high confidence" label means "the retriever found highly-similar passages and most slots passed validation" — it is not a probability of correctness.
- **No multi-pet optimization.** Each pet is scheduled independently. Conflicts between pets in the same household are detected by the existing `Scheduler.detect_conflicts()` but the AI layer does not jointly optimize across them.

## Could it be misused?

- **As a medical tool.** Owners might ask "should I give my dog Benadryl?" or "is my cat dehydrated?". The system has a deny-list scrubber that catches medical-claim language and replaces it with "Consult your veterinarian", and the system prompt instructs Claude to refuse medical specifics. This is a guardrail, not a guarantee — sufficiently roundabout queries could still slip through.
- **As authoritative scheduling.** A worried owner might trust the schedule over their own observation of the pet. Mitigation: every recommendation panel surfaces the "advisory only" caption, the confidence label, and the citations. Low-confidence outputs trigger a visible warning.
- **As a substitute for socialization or training.** The schedule cannot teach a dog to stop pulling on leash or train a cat to use a scratcher. The KB documents make this explicit; the system does not.

## What surprised me while testing

- **Retrieval quality without an LLM is already useful.** Running `evaluate.py` with `ANTHROPIC_API_KEY` unset still produces sensible schedules because the deterministic fallback uses real retrieval-grounded citations. The LLM adds polish and adaptive rationale, but the value of the retrieval layer is independently visible.
- **Auto-shift handles "owner busy 09:00–17:00" cleanly.** I expected this to need hand-tuning, but the 15-minute step search finds valid windows for high-energy dogs by relocating midday walks to early morning or late afternoon without intervention.
- **Cosine vs. keyword.** A test query like *"my hyper puppy is restless every afternoon"* retrieves `dog_high_energy_schedule.md` and `enrichment_high_energy_dog.md` at the top — neither contains the words "hyper", "puppy", "restless", or "afternoon". This is the textbook RAG advantage and it was satisfying to see it fire on real KB content.

## AI collaboration during the build

This project was built collaboratively with Claude (the Claude Code CLI). Required reflection per the rubric:

### One instance where AI gave a helpful suggestion

When designing the constraint engine, I planned to use exact-match time comparison ("two slots overlap if they have the same `time` string"). Claude pointed out that this misses the most common real case: two slots whose intervals overlap but whose start times differ. It suggested using **half-open `[start, end)` intervals in minutes-since-midnight**, which:
- Naturally handles `08:30 + 30min` overlapping `09:00 + 30min`
- Treats "ends exactly when busy begins" as non-overlapping (the right semantic)
- Generalizes to the auto-shift logic without special cases

This is now `recommender/constraint_engine.py:overlaps()`. I wouldn't have arrived at it as cleanly on my own.

### One instance where AI's suggestion was flawed

When generating the knowledge base, Claude initially suggested including specific medication dosages ("give 1mg/kg of meloxicam for arthritic seniors") in the senior-care doc. I rejected this — even though those numbers are findable in pet-care literature, embedding them in a system that surfaces them as citations creates a non-trivial risk of an owner self-medicating. I rewrote those passages to defer all dosing to a vet and added the medical-claim deny-list scrubber as a defense-in-depth measure.

The lesson: AI tools optimize for "completeness of answer" by default. Safety-critical applications need the human to draw the boundary on what *should* be in the system, not just what *can* be.

### How using separate agents helped me stay organized

I split the build into parallel agents: one for the knowledge base content, one for the `rag/` module, one for the `recommender/` module, one for tests + evaluation, one for documentation. This kept context windows focused — the agent writing markdown content didn't need to see Python module signatures, and vice versa. When two of the agents hit infrastructure timeouts mid-task, I was able to inspect their partial output and complete the remaining files myself without losing the original design intent, because each agent's scope was already delimited.

### What I learned about being the lead architect

The AI is fast at *fluent code* and slow at *correct boundaries*. I spent more time on the plan than on any single file: deciding where the LLM call lives, what the fallback path looks like, what the data classes contain, where the guardrails sit. Once those were settled, generating the code was nearly mechanical. If I had skipped the planning step and just asked an agent to "build the RAG system", I would have gotten something that worked in a demo but had no separation between retrieval, generation, validation, and ranking — and would have been impossible to test.

## Testing summary

- **Total tests:** 42 (29 pure-Python + 13 RAG, 2 RAG live-tests gated on `RUN_RAG_LIVE_TESTS=1`).
- **Coverage areas:** existing scheduler (8 tests, unchanged), constraint engine + ranker (21 tests), feature builder, frontmatter parsing, chunking, guardrail, prompt construction, fallback path, and live ingest+query roundtrip.
- **Evaluation harness:** `evaluate.py` runs 6 scenarios end-to-end:
  1. High-energy dog with 9-5 owner — must produce ≥3 kept slots, none in busy window.
  2. Senior cat, mostly-busy owner — must produce ≥2 kept slots, none in busy window.
  3. Dog with existing morning walk + feeding — recommender must avoid these.
  4. Owner fully available — should keep most proposals.
  5. Rabbit ('other' species) fallback path — should still produce ≥2 valid slots.
  6. Adversarial: only 07:00–08:00 free — auto-shift must find the window.

When run with `ANTHROPIC_API_KEY` set: average confidence ~0.70, used_llm=True for all scenarios.
When run without an API key (template fallback): average confidence ~0.50, used_llm=False, all constraint-validation checks still pass.

## Confidence

★★★★☆ — the core retrieval, constraint validation, and ranking are well-tested and behaviorally robust. The remaining uncertainty is around LLM output variance: Claude occasionally produces tasks whose rationale doesn't faithfully cite a source, which the citation backfill in `rag_engine.py` masks but doesn't fully fix. A future iteration would add a second LLM pass that scores rationale–context faithfulness explicitly.
