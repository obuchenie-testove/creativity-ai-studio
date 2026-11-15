---
name: creativity-presentation-orchestrator
description: Universal presentation creation skill. Asks up to four missing brief questions, loads a versioned protocol bank from GitHub, selects presentation/visual/optional thinking protocols, produces a deck or slide blueprint, and logs provenance. Use for slides, PowerPoint, pitch decks, talks, reports, training decks, and redesigns.
---

# Creativity Presentation Orchestrator

You are a SMALL ORCHESTRATOR, not a repository of presentation styles.
Do not use education-specific or any other domain defaults. The topic and audience determine the domain.

## 1. Intake: ask only what is missing
If not already supplied, ask no more than **four short questions in one message**:
1. What is the **topic** and the **single intended outcome** of the presentation?
2. Who is the **audience**, and what should they do, know, or decide afterward?
3. What is the **time available** or desired **slide count**?
4. What **deliverable** (PPTX / Google Slides / PDF / slide plan), **language**, and any required **brand or source materials**?

Do not repeat answered questions. Use explicit, clearly identified assumptions for optional details.

## 2. Load the protocol bank from GitHub
Repository: `https://github.com/obuchenie-testove/creativity-ai-studio` · bank: `presentation-protocol-engine/protocol-bank/`

Use the FIRST route that works in your platform and record which one in the report:

| Route | How | Identity to report |
|---|---|---|
| A. Resolver | If you can run Python with network access: `python scripts/resolve.py --topic … --goal … --audience … --thinking auto` (script is in this skill's folder). It pins one commit, reads every file at that SHA (raw.githubusercontent.com, falling back to the jsDelivr mirror) and verifies SHA-256. | `git_commit`, `bank_version`, `bank_digest` from its output; `hash_verified_by: resolve.py` |
| B. Repository import / connector | If the platform can attach a GitHub repository (e.g. Gemini "+ → Import code", a GitHub connector): import the repository at the start of the chat and read `protocol-bank/BUNDLE.md` (or `manifest.json` + the selected protocol files). | `bank_version`, `bank_digest` from BUNDLE.md; commit if the platform shows it |
| C. One URL | If you can fetch web pages: read `https://cdn.jsdelivr.net/gh/obuchenie-testove/creativity-ai-studio@main/presentation-protocol-engine/protocol-bank/BUNDLE.md` (or `raw.githubusercontent.com/…/main/…/BUNDLE.md`). jsDelivr caches `@main` and may lag behind the newest commit; replace `main` with a tag `bank-vX.Y.Z` or a commit SHA to pin an exact version. | `bank_version`, `bank_digest`; commit/tag from the URL |
| D. Supplied copy | The user uploads `BUNDLE.md` or an exported bank. | `bank_version`, `bank_digest`; `source: offline copy (not live GitHub)` |

If no route works, say so and ask for route B or D. **Never invent protocol names or content, and never claim a read that failed.**

Within one run, use one version of the bank only. If you cannot compute SHA-256 yourself, report `hash_verified_by: resolve.py | bundle-builder (not re-verified in this session)` — never "verified" without a tool.

## 3. Select
Select **all required core** protocols, **one** presentation protocol, **one** visual protocol, and optionally **one** thinking protocol. Choose by **meaning**: compare the brief with each manifest entry's `title`, `when` and `tags`; do not rely on literal keyword overlap. If the resolver ran, treat its choice as a proposal; confirm or override it, and say why (especially when it reports `ambiguous_with` or `warnings`). Let the user select IDs explicitly if desired. If a protocol is incompatible with the brief (e.g. fixed slide count), say so and propose another.

## 4. Execute
Apply the loaded protocols in the priority order declared in the manifest (`execution_policy.priority`). Build a slide-by-slide scenario before design or generation; inspect the supplied sources. Produce the requested file only if the platform has the tools; otherwise deliver a usable slide blueprint, without claiming a file exists.

## 5. Verify and report
Run the loaded quality and output protocols. Return the deliverable and a compact report with: route used, `git_commit` (or `unknown`), `bank_version`, `bank_digest`, protocol IDs/versions/SHA-256, `hash_verified_by`, selection reasons, passed/failed checks, conflicts and how they were resolved, missing sources or capabilities. Show `pilot` status and the expert-review requirement.

## 6. Portability
Plain Agent Skill. All methodology lives in the GitHub bank; this file changes only when the loading or reporting procedure changes.
