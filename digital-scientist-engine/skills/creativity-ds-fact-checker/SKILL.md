---
name: creativity-ds-fact-checker
description: Verifies every factual claim and citation in a Creativity LTD digital scientist text before publication, with source links and verdicts. Loads core protocols + task-claim-check + role-source-scout + role-evaluator + source-scholarly-mcp from the GitHub bank. Suited to search-first systems such as Perplexity.
---

# Creativity DS — Fact Checker

1. Load (one pinned commit): `core-governance`, `core-identity`, `core-output`, `role-source-scout`, `role-evaluator`, `role-completer`, `task-claim-check`, `source-scholarly-mcp`.
2. Extract every factual claim (dates, names, institutions, studies, quotes) into a list.
3. For each: the source found (URL/DOI), whether it was actually opened, verdict (supported / partly / not supported / unverifiable), and the exact corrected wording when needed.
4. Claims about Creativity itself are checked only against the context the human provided; never "confirm" them from your own assumptions.
5. Add the provenance block.
