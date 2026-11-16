# Creativity Digital Scientist Protocol Engine — Pilot v0.1.0

Protocol-driven, provider-neutral **digital scientist** skills by **Creativity LTD (Креативност ЕООД)**. Same architecture as `presentation-protocol-engine/`: small skills, a version-pinned protocol bank on GitHub, hash verification, provenance report.

> **Definition (canonical):** „Дигиталният учен е AI колега с ясна роля в изследователския екип и проверими умения, който работи под ръководството на човек изследовател и е свързан с реални научни бази данни.“
> Pillar article: https://cpocreativity.com/digitalen-uchen/

## Architecture

**Small skill** → **short brief** → **pin one Git commit** → **read manifest** → **load required core + 1–5 roles + 1 task + 0–2 sources** → **run roles in order (completer last)** → **report with provenance**.

| Layer | Protocols | Rule |
|---|---|---|
| Core (always) | `core-governance`, `core-identity`, `core-output` | Human leads; every claim has a traceable source or is marked unverified; exact definition; no internal methodology; provenance report |
| Roles (1–5) | `role-source-scout`, `role-explorer`, `role-evaluator`, `role-specialist`, `role-completer` | Five functional roles inspired by Belbin's team roles; the evaluator counters AI agreeableness |
| Task (exactly 1) | `task-literature-scan`, `task-claim-check`, `task-hypothesis-challenge`, `task-source-structuring`, `task-series-article`, `task-aeo-geo-review` | What is being done |
| Sources (0–2) | `source-scholarly-mcp` | OpenAlex, Crossref, Semantic Scholar, arXiv, PubMed via MCP/API when the host has them |

## Skills

| Skill | Purpose | Typical host |
|---|---|---|
| `skills/creativity-digital-scientist` | Orchestrator for any research-style task | Claude, Gemini, ChatGPT, DeepSeek |
| `skills/creativity-ds-series-author` | Writes the next article of the positioning series | ChatGPT |
| `skills/creativity-ds-reviewer` | AEO/GEO + concept review with ready fixes | Gemini |
| `skills/creativity-ds-fact-checker` | Claim-by-claim verification with sources | Perplexity |

## Public layer only

This repository is **public**. It contains only the public-safe layer. Creativity's internal protocols (the full skill bank, the internal methodology for turning sources into working protocols, internal knowledge representation) are **not** here and are supplied privately when authorised. A host must never try to reconstruct them.

## Install in another AI system

Install a `SKILL.md` as an Agent Skill, or paste it as system/project instructions, and allow read access to this public repository. Python environments can run the resolver:

```bash
python scripts/resolve.py --question "Провери твърденията в статията" --goal "проверка преди публикуване" --output /tmp/ds-context.json
```

The resolver only resolves and verifies protocols; the host AI does the work.

**Live catalog:** `https://raw.githubusercontent.com/obuchenie-testove/creativity-ai-studio/main/digital-scientist-engine/protocol-bank/manifest.json`

## Updating protocols without touching the skills

Edit a protocol JSON, bump its `version`, then update `version` and `sha256` in `protocol-bank/manifest.json` **in the same commit**. Old runs stay reproducible from their recorded commit SHA.

## Verification

```bash
python -m unittest discover -s tests -v
```

Status: **pilot — owner review required**. See `AGENTS.md` for instructions to other AI systems.
