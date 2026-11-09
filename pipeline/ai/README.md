# AI classification without a paid service (step 5b)

Owner's decision 09.11.2026: no paid API for now. Claude classifies outlets **in a chat session**
(covered by the owner's existing Claude plan), country by country, top 50 per country.

1. `python pipeline/ai/prepare.py COD KEN ... [--top 50]` -> short profiles in `work/ai_input/<ISO3>.json`
   (already classified outlets are skipped).
2. Claude reads the profiles and writes its answers into `cache/ai_classification.json`:
   only from the outlet's own texts (no guessing from general knowledge), only ids from
   `config/categories.yaml` / `config/topic_keywords.yaml`, each value with a short reason.
   Also: owner name / ownership if the text says so, and a warning when the website no longer
   belongs to the outlet (casino, travel guide, parked domain ...).
3. `pipeline/classify/classify.py` uses the answers as method `ai_classification`
   (after website check, before word lists); they never replace stronger evidence.

Later (owner may get another plan): the same answers can be produced for all outlets through the
Claude API in a GitHub workflow; the cache format stays the same.
