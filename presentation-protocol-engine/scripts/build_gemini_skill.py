#!/usr/bin/env python3
"""Build the Gemini app skill: dist/creativity-presentation-orchestrator-gemini.zip

Gemini app skills cannot run scripts that use the internet, so this package has
no resolver. It carries the protocol bank as reference files (byte-for-byte, so
the manifest hashes still match) and instructions that prefer a newer bank when
the GitHub repository is imported into the chat.

Usage: python scripts/build_gemini_skill.py
"""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "protocol-bank"
DIST = ROOT / "dist"
NAME = "creativity-presentation-orchestrator"

SKILL = """---
name: {name}
description: Creates presentations (slides, pitch decks, talks, reports, trainings, lessons) by the Creativity LTD protocol bank. Asks up to four brief questions, selects presentation, visual and optional thinking protocols, builds a slide-by-slide plan or file, and reports which protocol versions it used.
---

# Creativity Presentation Orchestrator

You organise the work; the methodology lives in the Creativity protocol bank. Do not use domain defaults: the topic and audience decide the domain.

## Protocol bank
- Bundled copy: `references/manifest.json` and the protocol files in `references/core/`, `references/presentation/`, `references/visual/`, `references/thinking/`. Bank version {version}, bank digest `{digest}`.
- Newer version: if the GitHub repository obuchenie-testove/creativity-ai-studio has been imported into this chat, read `presentation-protocol-engine/protocol-bank/manifest.json` there. If its `version` is higher than {version}, use that bank instead and say so.
- Use only protocols that exist in the bank. If a file is missing, say so; do not invent protocols or their content.

## 1. Brief
If missing, ask in one message at most four short questions: topic and intended outcome; audience and what they should do afterwards; time or number of slides; format, language and source materials. Do not repeat answered questions.

## 2. Select
Take all protocols listed in `execution_policy.required_protocols`, one presentation protocol, one visual protocol and optionally one thinking protocol. Choose by meaning: compare the brief with each manifest entry's `title`, `when` and `tags`. If a protocol does not fit the brief (for example a fixed slide count), say so and choose another.

## 3. Create
Apply the protocols in the order of `execution_policy.priority`. Build the slide-by-slide plan first: number, purpose, key message, visual idea, source if needed, speaker notes. Do not invent facts, figures or quotes; mark anything unverified. Create a file only if you have a tool for it; otherwise give the complete slide plan and do not claim a file exists.

## 4. Report
End with a short report: bank version and digest (and whether it came from the bundled copy or the imported repository); selected protocol IDs and versions with the reason for each choice; checks passed and failed according to the loaded quality and output protocols; conflicts and how they were resolved; missing sources or capabilities. The protocol hashes in the manifest were computed when the bank was published; you do not recompute them. Note that the protocols are pilot status and the result needs expert review.
"""


def main():
    manifest_raw = (BANK / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    out = DIST / "gemini" / NAME
    if out.exists():
        shutil.rmtree(out)
    (out / "references").mkdir(parents=True)
    (out / "SKILL.md").write_text(SKILL.format(name=NAME, version=manifest["version"],
                                               digest=hashlib.sha256(manifest_raw).hexdigest()), encoding="utf-8")
    shutil.copyfile(BANK / "manifest.json", out / "references" / "manifest.json")
    for e in manifest["entries"]:
        src = BANK / e["path"]
        if hashlib.sha256(src.read_bytes()).hexdigest() != e["sha256"]:
            raise SystemExit(f"SHA256 mismatch for {e['id']}")
        dest = out / "references" / e["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    zip_path = DIST / f"{NAME}-gemini.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(out.parent))
    print(f"Wrote {zip_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
