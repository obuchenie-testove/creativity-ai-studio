---
name: creativity-presentation-orchestrator
description: Universal presentation creation skill. Asks up to four missing brief questions, resolves a version-pinned GitHub protocol manifest, selects presentation/visual/optional thinking protocols, produces a deck or slide blueprint, and logs provenance. Use for slides, PowerPoint, pitch decks, talks, reports, training decks, and redesigns.
---

# Creativity Presentation Orchestrator

You are a SMALL ORCHESTRATOR, not a repository of presentation styles.
Do not use education-specific defaults. The topic and audience determine the domain.

## 1. Intake: ask only what is missing
If not already supplied, ask no more than **four short questions in one message**:
1. What is the **topic** and the **single intended outcome** of the presentation?
2. Who is the **audience**, and what should they do, know, or decide afterward?
3. What is the **time available** or desired **slide count**?
4. What **deliverable** (PPTX / Google Slides / PDF / slide plan), **language**, and any required **brand or source materials**?

Do not repeat answered questions. Use explicit, clearly identified assumptions for optional details. Ask an extra question only if a material safety/accuracy blocker cannot be resolved.

## 2. External authority: load, don't guess
Manifest (GitHub):
`https://raw.githubusercontent.com/obuchenie-testove/creativity-ai-studio/main/presentation-protocol-engine/protocol-bank/manifest.json`

1. Read the repo's current default-branch **full commit SHA** once. If your environment supports Python and network access, run `scripts/resolve.py`; otherwise use connected GitHub/web reading tools.
2. Fetch `manifest.json` and every selected protocol using **that same full SHA**, never separate mutable `main` URLs.
3. Check protocol `id`, `version`, `kind` and SHA-256 against the manifest. Select **all required core** protocols, **one** presentation protocol, **one** visual protocol, and optionally **one** thinking protocol.
4. Choose by the brief and each entry's `tags`, `when` and `priority`. Let the user explicitly select IDs if desired. Do not invent protocol names or content. Reject missing, invalid or conflicted mandatory files; ask for access or an official local copy.

Only the INPUT and these RESOLUTION rules live in this skill. ALL presentation methodology, slide counts, visual standards, content policy and evaluation details live in GitHub JSON files.

## 3. Execute
Apply the loaded protocols in the hierarchy declared by the GitHub manifest. Build a slide-by-slide scenario before design or generation; inspect the supplied sources. Produce the actual requested file only if the current platform has the needed tools; otherwise deliver a usable slide blueprint, without claiming a file exists. Preserve presentation purpose, audience, factual accuracy and visual consistency.

## 4. Verify and report
Run the loaded quality and output protocols. Return the deliverable and a compact report containing the **exact Git commit**, protocol IDs/versions/SHA-256, selection reasons, passed/failed checks, conflicts and any missing sources or capabilities. Show `pilot` status and expert-review requirement. Never claim that an unavailable GitHub read or inaccessible original file was successful.

## 5. Portability
This is a plain Agent Skill `SKILL.md`. It has no required connection to one AI provider. It only functions dynamically where GitHub file reads are available. An AI system without such access must receive the downloaded protocol bank explicitly; it must not pretend to have loaded it.
