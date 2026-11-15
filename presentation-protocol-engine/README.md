# Creativity Presentation Protocol Engine — Pilot v0.1.0

A **provider-neutral**, protocol-driven presentation skill by Creativity LTD. **Not** an ObrazovanieBG project.

## Architecture

**Small skill** → **four-question brief** → **pin GitHub commit** → **read manifest** → **load required core + 1 presentation + 1 visual + optional thinking protocol** → **plan / render (if tools exist)** → **evaluate + log provenance**.

The skill deliberately contains no pedagogical template, color palette, slide-count heuristic or presentation methodology. All standards live in `protocol-bank/` and can change independently of `SKILL.md`.

## Install in another AI system

Install `skills/creativity-presentation-orchestrator/SKILL.md` as an Agent Skill, or paste its text as system/project instructions. Grant the system read-only GitHub access to this public repository. For Python-based environments, `scripts/resolve.py` can pin one commit, verify SHA-256 and emit a protocol context JSON. For environments without network access, supply a locally exported copy of the bank; external auto-update then **does not** occur.

**Live catalog:** `https://raw.githubusercontent.com/obuchenie-testove/creativity-ai-studio/main/presentation-protocol-engine/protocol-bank/manifest.json`

Example:

```bash
python scripts/resolve.py --topic "New product launch" --goal "Obtain approval" --audience "Leadership" --minutes 12 --presentation present-pitch --visual visual-clean --output /tmp/presentation-context.json
```

This command resolves and downloads the protocols. **It does not produce PPTX** by itself; the hosting AI system subsequently builds the deck according to the loaded rules.

## Catalog status and provenance

The pilot catalog adapts 14 presentation and 6 thinking approaches from the Creativity Visual Protocol Studio snapshot (24 Oct 2026), plus 3 generic visual protocols. An older CreAItivity Presentation Prompt Generator provided labels/links for 15 additional visual styles; since its remote JSON files could not be retrieved for verification, these 15 are **new concise adaptations**, explicitly identified inside their JSON files — **not verbatim imports**. Source materials were user-provided / user-owned and public editorial material, and the protocol definitions must undergo domain-expert approval before production use.

## Updating the bank without editing the skill

Edit a protocol JSON and change its `version`, then update that entry's `sha256` and `version` in `protocol-bank/manifest.json` **in the same commit**. Next run resolves the branch HEAD again and reads the new version. Old runs remain reproducible from their recorded full commit SHA.

## Verification

```bash
python -m unittest discover -s tests -v
```

## How to download

From GitHub, select **Code → Download ZIP** for the repository; the project is under `presentation-protocol-engine/`. Alternatively use the separate local ZIP distributed with the skill. Keep GitHub access available for live protocol updates.
