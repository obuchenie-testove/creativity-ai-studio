# Creativity Presentation Protocol Engine — Pilot v0.2.0

A **provider-neutral**, protocol-driven presentation skill by Creativity LTD.

## Idea

The **skill** runs the work; **GitHub** keeps the standards it works by. The skill reads the request, decides which rules it needs and loads only those. The standards live in a versioned protocol bank and change without editing the skill. One large static prompt becomes a set of modules combined per task.

- **Skill (orchestrator)** — `skills/creativity-presentation-orchestrator/`: intake (≤ 4 questions), loading, selection, execution, verification, provenance report. No methodology inside.
- **Protocol bank** — `protocol-bank/`: `manifest.json` (what each protocol does, when it applies, which version is current) + one JSON file per protocol: 3 core, 14 presentation, 18 visual, 6 thinking.
- **Resolver** — `skills/…/scripts/resolve.py`: deterministic helper (not AI). Pins one commit, verifies SHA-256 and metadata, proposes protocols, fails closed.
- **Host AI** — the model in ChatGPT, Claude, Gemini, etc. It understands the brief, confirms the selection by meaning, builds the deck or slide plan, reviews it and reports. File export depends on the host's tools.
- **Human** — final expert approval.

## How each platform reaches GitHub

| Route | Works where | What it reads |
|---|---|---|
| **A. Resolver** | Python + network (Claude Code, local agents, CI) | GitHub API → commit SHA → files from `raw.githubusercontent.com` at that SHA; **falls back to the jsDelivr mirror** of the same SHA when raw is blocked |
| **B. Repository import / connector** | Gemini (**+ → Import code** → repository URL), platforms with a GitHub connector | `protocol-bank/BUNDLE.md` (or manifest + protocol files). Import at the start of each chat to get the current version |
| **C. One URL** | Any platform that can fetch a web page | `https://cdn.jsdelivr.net/gh/obuchenie-testove/creativity-ai-studio@<bank-vX.Y.Z or SHA>/presentation-protocol-engine/protocol-bank/BUNDLE.md` |
| **D. Supplied copy** | Anything that accepts an uploaded file | `BUNDLE.md` from the latest GitHub release |

`PERMISSION_DENIED` on `raw.githubusercontent.com` is a platform restriction, not a repository problem; use route B, C or D.

**Version identity on every route:** `bank_version` (manifest `version`) + `bank_digest` (SHA-256 of `manifest.json`, which contains every protocol hash). The tag `bank-v<version>` maps a version to its commit. The resolver additionally reports the exact `git_commit`.

## Install the skill

Install the folder `skills/creativity-presentation-orchestrator/` (SKILL.md + scripts/) as an Agent Skill, or paste `SKILL.md` into the platform's custom instructions. Nothing else is needed: the skill loads the bank from GitHub by the routes above.

```bash
python skills/creativity-presentation-orchestrator/scripts/resolve.py \
  --topic "Нов продукт" --goal "Одобрение" --audience "Ръководство" --slides 12 --thinking auto
# offline copy of the bank, with the commit it was exported from:
python skills/creativity-presentation-orchestrator/scripts/resolve.py ... --local protocol-bank --snapshot-commit <sha>
```

The resolver **does not produce PPTX**. Its output (protocols, selection reasons, `ambiguous_with`, `warnings`, provenance) goes to the host AI.

## Update the bank without editing the skill

1. Edit a protocol JSON file and raise its `version`.
2. `python scripts/sync_manifest.py` — copies versions, recomputes SHA-256 in `manifest.json`, rebuilds `BUNDLE.md`. It refuses content changes without a version bump.
3. For a bank release raise `version` in `manifest.json`, run `python scripts/build_bundle.py`, commit, then push a tag `bank-v<version>`. The workflow verifies the tag and publishes a GitHub release with `BUNDLE.md`.
4. The next run reads the new version; old runs stay reproducible from their commit or tag.

## Verification

```bash
python -m unittest discover -s tests -v      # 32 tests: golden selection set (BG/EN), live mode with mocked GitHub, jsDelivr fallback, fail-closed cases, CLI
python scripts/sync_manifest.py --check
python scripts/build_bundle.py --check
```

GitHub Actions runs the same checks on every pull request and push to `main` (`.github/workflows/presentation-protocol-engine.yml`).

## Catalog status and provenance

All protocols are `pilot`. 14 presentation and 6 thinking approaches are adapted from the Creativity Visual Protocol Studio snapshot (24 Oct 2026); 15 visual styles are new concise adaptations of labels from the older CreAItivity Presentation Prompt Generator (originals not verifiable, marked in each file); 3 visual protocols are generic. Protocol definitions require domain-expert approval before production use.

## Changelog

- **0.2.0** — Access routes for every platform (resolver, repository import, one URL, uploaded copy); jsDelivr fallback; single-file `BUNDLE.md`; `bank_version`/`bank_digest` identity; offline `--snapshot-commit`; bilingual BG/EN tags and specificity priorities; Cyrillic word-start matching; `--thinking auto`; tie and slide-count warnings; enforcement of required core protocols, allowed status, defaults and safe paths; resolver moved into the skill folder; 32 tests; CI and release workflow. Protocol files unchanged.
- **0.1.0** — Initial pilot.
