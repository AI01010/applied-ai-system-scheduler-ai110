[notice] To update, run: python.exe -m pip install --upgrade pip       python main.py
>> env) PS C:\Saad\Programming\Codepath\AI110\applied-ai-system-final> 

============================================================
  1. Household setup
============================================================
Owner: Jordan, busy [('09:00', '17:00')]
Pets:  [('Mochi', 'dog', 'high', 3), ('Luna', 'cat', 'low', 11)]

============================================================
  2. Existing rule-based schedule (no AI)
============================================================
  [    ] 07:00  Feeding              (Luna) — daily
  [    ] 07:30  Morning walk         (Mochi) — daily

============================================================
  3. RAG pipeline — ingest -> retrieve -> generate
============================================================
Building local Chroma index from data/knowledge_base/...
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
modules.json: 100%|███████████████████████████████████████████████████████████| 349/349 [00:00<?, ?B/s]
C:\Saad\Programming\Codepath\AI110\applied-ai-system-final\.venv\Lib\site-packages\huggingface_hub\file_download.py:138: UserWarning: `huggingface_hub` cache-system uses symlinks by default to efficiently store duplicated files but your machine does not support them in C:\Users\ashraful\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2. Caching files will still work but in a degraded version that might require more space on your disk. This warning can be disabled by setting the `HF_HUB_DISABLE_SYMLINKS_WARNING` environment variable. For more details, see https://huggingface.co/docs/huggingface_hub/how-to-cache#limitations.
To support symlinks on Windows, you either need to activate Developer Mode or to run Python as an administrator. In order to activate developer mode, see this article: https://docs.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development
  warnings.warn(message)
config_sentence_transformers.json: 100%|██████████████████████████████████████| 116/116 [00:00<?, ?B/s]
README.md: 10.5kB [00:00, ?B/s]
sentence_bert_config.json: 100%|████████████████████████████████████| 53.0/53.0 [00:00<00:00, 55.7kB/s]
config.json: 100%|████████████████████████████████████████████████████████████| 612/612 [00:00<?, ?B/s]
model.safetensors: 100%|██████████████████████████████████████████| 90.9M/90.9M [00:03<00:00, 28.2MB/s]
Loading weights: 100%|█████████████████████████████████████████████| 103/103 [00:00<00:00, 4481.47it/s]
tokenizer_config.json: 100%|██████████████████████████████████████████████████| 350/350 [00:00<?, ?B/s]
vocab.txt: 232kB [00:00, 8.79MB/s]
tokenizer.json: 466kB [00:00, 16.8MB/s]
special_tokens_map.json: 100%|████████████████████████████████████████████████| 112/112 [00:00<?, ?B/s]
config.json: 100%|████████████████████████████████████████████████████████████| 190/190 [00:00<?, ?B/s]
Index ready: 319 chunks in collection 'pawpal_kb'.

============================================================
  4. AI recommendations for Mochi the dog
============================================================
C:\Saad\Programming\Codepath\AI110\applied-ai-system-final\rag\rag_engine.py:154: FutureWarning: 

All support for the `google.generativeai` package has ended. It will no longer be receiving 
updates or bug fixes. Please switch to the `google.genai` package as soon as possible.
See README for more details:

https://github.com/google-gemini/deprecated-generative-ai-python/blob/main/README.md

  import google.generativeai as genai  # type: ignore
  provider:       template  (used_llm=False)
  retrieval avg:  0.615
  citations:      ['conflict_walk_overlaps_meds.md', 'dog_low_energy_schedule.md', 'dog_high_energy_schedule.md']...
  explanation:    Default schedule for a high-energy dog. LLM was not called (no API key or call failed); recommendati...

  Confidence: 0.77 (HIGH)
  Kept: 5  Dropped: 0

  Ranked schedule:
   * 08:00  Morning walk           score=0.77  (high)
   * 17:00  Midday play            score=0.77  (medium)
     18:00  Evening walk           score=0.77  (high)
     08:30  Feeding                score=0.77  (high)
     18:45  Feeding                score=0.77  (high)

============================================================
  4. AI recommendations for Luna the cat
============================================================
  provider:       template  (used_llm=False)
  retrieval avg:  0.605
  citations:      ['cat_senior_care.md', 'cat_adult_care.md', 'schedule_wfh_multi_pet.md']...
  explanation:    Default schedule for a low-energy cat. LLM was not called (no API key or call failed); recommendatio...

  Confidence: 0.76 (HIGH)
  Kept: 5  Dropped: 0

  Ranked schedule:
     07:30  Feeding                score=0.76  (high)
   * 17:00  Play session           score=0.76  (medium)
   * 17:00  Litter check           score=0.76  (medium)
     18:00  Feeding                score=0.76  (high)
     19:30  Evening play           score=0.76  (low)

============================================================
  5. Top retrieval hits for Mochi (debug view)
============================================================
Query:
  Daily care schedule for a 3-year-old high-energy dog named Mochi. Owner busy 09:00-17:00. Existing tasks: Morning walk at 07:30. Health notes: none.

  [1] score=0.634  source=dog_low_energy_schedule.md
      # Low-Energy Dog Daily Schedule...
  [2] score=0.627  source=dog_adult_care.md
      # Adult Dog Daily Care (1 to 7 years)...
  [3] score=0.621  source=dog_high_energy_schedule.md
      # High-Energy Dog Daily Schedule...
  [4] score=0.601  source=conflict_two_pets_same_feed_time.md
      Schedule entry: "08:00 — Mochi feeding | 08:10 — Luna feeding"...
  [5] score=0.595  source=conflict_walk_overlaps_meds.md
      A common conflict: the dog's morning walk is scheduled for 08:00, but a daily medication needs to be given at 08:00 with food....

(.venv) PS C:\Saad\Programming\Codepath\AI110\applied-ai-system-final> python -m pytest -v
>> 
========================================= test session starts =========================================
platform win32 -- Python 3.11.9, pytest-9.0.3, pluggy-1.6.0 -- C:\Saad\Programming\Codepath\AI110\applied-ai-system-final\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Saad\Programming\Codepath\AI110\applied-ai-system-final
plugins: anyio-4.13.0
collected 45 items                                                                                     

tests/test_pawpal.py::test_mark_complete_changes_status PASSED                                   [  2%]
tests/test_pawpal.py::test_add_task_increases_count PASSED                                       [  4%]
tests/test_pawpal.py::test_sort_by_time_chronological PASSED                                     [  6%]
tests/test_pawpal.py::test_recurring_daily_advances_due_date PASSED                              [  8%]
tests/test_pawpal.py::test_recurring_weekly_advances_due_date PASSED                             [ 11%]
tests/test_pawpal.py::test_conflict_detection_flags_same_time PASSED                             [ 13%]
tests/test_pawpal.py::test_no_conflict_different_times PASSED                                    [ 15%]
tests/test_pawpal.py::test_filter_by_status_returns_incomplete PASSED                            [ 17%]
tests/test_rag.py::test_build_query_includes_signal_words PASSED                                 [ 20%]
tests/test_rag.py::test_build_query_handles_missing_fields PASSED                                [ 22%]
tests/test_rag.py::test_parse_frontmatter_extracts_kv PASSED                                     [ 24%]
tests/test_rag.py::test_parse_frontmatter_no_block PASSED                                        [ 26%]
tests/test_rag.py::test_chunk_text_splits_paragraphs PASSED                                      [ 28%]
tests/test_rag.py::test_chunk_text_splits_long_paragraph_on_sentences PASSED                     [ 31%]
tests/test_rag.py::test_scrub_medical_claims_triggers_on_diagnose PASSED                         [ 33%]
tests/test_rag.py::test_scrub_medical_claims_passes_clean_text PASSED                            [ 35%]
tests/test_rag.py::test_strip_json_fence_removes_markdown_fences PASSED                          [ 37%]
tests/test_rag.py::test_build_user_prompt_embeds_context PASSED                                  [ 40%]
tests/test_rag.py::test_fallback_template_dog_high PASSED                                        [ 42%]
tests/test_rag.py::test_fallback_template_cat PASSED                                             [ 44%]
tests/test_rag.py::test_fallback_template_unknown_species PASSED                                 [ 46%]
tests/test_rag.py::test_recommendation_default_fields PASSED                                     [ 48%]
tests/test_rag.py::test_embedder_shape SKIPPED (set RUN_RAG_LIVE_TESTS=1 to run)                 [ 51%]
tests/test_rag.py::test_chroma_ingest_and_query_roundtrip SKIPPED (set RUN_RAG_LIVE_TESTS=1 ...) [ 53%]
tests/test_recommender.py::test_parse_hhmm_basic PASSED                                          [ 55%]
tests/test_recommender.py::test_parse_hhmm_rejects_garbage PASSED                                [ 57%]
tests/test_recommender.py::test_overlaps_half_open PASSED                                        [ 60%]
tests/test_recommender.py::test_slot_minutes_default_duration PASSED                             [ 62%]
tests/test_recommender.py::test_violates_busy_times_true PASSED                                  [ 64%]
tests/test_recommender.py::test_violates_busy_times_false_when_outside PASSED                    [ 66%]
tests/test_recommender.py::test_violates_busy_times_adjacent_is_ok PASSED                        [ 68%]
tests/test_recommender.py::test_conflicts_with_existing_task PASSED                              [ 71%]
tests/test_recommender.py::test_no_conflict_with_distant_task PASSED                             [ 73%]
tests/test_recommender.py::test_auto_shift_finds_next_valid_slot PASSED                          [ 75%]
tests/test_recommender.py::test_auto_shift_returns_none_when_impossible PASSED                   [ 77%]
tests/test_recommender.py::test_validate_slots_keeps_clean_slots PASSED                          [ 80%]
tests/test_recommender.py::test_validate_slots_auto_shifts_violators PASSED                      [ 82%]
tests/test_recommender.py::test_validate_slots_drops_when_auto_fix_disabled PASSED               [ 84%]
tests/test_recommender.py::test_validate_slots_handles_malformed PASSED                          [ 86%]
tests/test_recommender.py::test_slot_score_components PASSED                                     [ 88%]
tests/test_recommender.py::test_rank_slots_orders_satisfied_first PASSED                         [ 91%]
tests/test_recommender.py::test_confidence_score_formula PASSED                                  [ 93%]
tests/test_recommender.py::test_confidence_score_zero_without_hits PASSED                        [ 95%]
tests/test_recommender.py::test_confidence_label_buckets PASSED                                  [ 97%]
tests/test_recommender.py::test_apply_recommendation_end_to_end PASSED                           [100%]

==================================== 43 passed, 2 skipped in 0.23s ====================================
(.venv) PS C:\Saad\Programming\Codepath\AI110\applied-ai-system-final> python evaluate.py
>> 
========================================================================
PawPal+ AI — Evaluation Harness
========================================================================

[setup] Building local Chroma index from data/knowledge_base/...
[setup] Index ready: 319 chunks.

[1/6] High-energy dog with 9-5 owner
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████████████████████████████| 103/103 [00:00<00:00, 1622.58it/s]
C:\Saad\Programming\Codepath\AI110\applied-ai-system-final\rag\rag_engine.py:154: FutureWarning: 

All support for the `google.generativeai` package has ended. It will no longer be receiving 
updates or bug fixes. Please switch to the `google.genai` package as soon as possible.
See README for more details:

https://github.com/google-gemini/deprecated-generative-ai-python/blob/main/README.md

  import google.generativeai as genai  # type: ignore
   confidence: 0.79 (high)  used_llm=False  kept=5  dropped=0
   PASS  no busy-time overlaps
   PASS  kept=5 (min=3)

[2/6] Senior cat, mostly-busy owner
   confidence: 0.75 (high)  used_llm=False  kept=5  dropped=0
   PASS  no busy-time overlaps
   PASS  kept=5 (min=2)

[3/6] Dog with existing tasks — recommender must avoid them
   confidence: 0.78 (high)  used_llm=False  kept=4  dropped=0
   PASS  no busy-time overlaps
   PASS  kept=4 (min=1)

[4/6] Owner fully available — should keep everything
   confidence: 0.79 (high)  used_llm=False  kept=4  dropped=0
   PASS  kept=4 (min=3)

[5/6] Rabbit ('other' species) fallback path
   confidence: 0.73 (high)  used_llm=False  kept=3  dropped=0
   PASS  no busy-time overlaps
   PASS  kept=3 (min=2)

[6/6] Adversarial: only 07:00-08:00 window free
   confidence: 0.78 (high)  used_llm=False  kept=4  dropped=0
   PASS  no busy-time overlaps

========================================================================
Summary
========================================================================
  scenarios:    6
  checks:       10 / 10 passed
  avg conf:     0.77  (min=0.73, max=0.79)

(.venv) PS C:\Saad\Programming\Codepath\AI110\applied-ai-system-final> 