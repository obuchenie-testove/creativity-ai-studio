#!/usr/bin/env python3
"""Build a kindergarten protocol bank + manifest + skill from one raw engine JSON (exchange format).

Usage: python3 build_kg.py raw/kg-ai-guardian.json [--date 2026-11-16]
Writes kindergarten-ds/<engine>/{protocol-bank/,skill/<skill-name>/SKILL.md,SYSTEM.md}.
Validation is strict: fails on anything that breaks the shared rules of the competition.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "obuchenie-testove/creativity-ai-studio"
AUTHORS = {
    "kg-play-design": "ChatGPT (OpenAI)",
    "kg-child-development": "Gemini (Google)",
    "kg-evidence-lab": "DeepSeek",
    "kg-family-team": "Qwen (Alibaba)",
    "kg-ai-guardian": "Claude (Anthropic)",
}
FOLDER = {"core": "core", "role": "roles", "task": "tasks", "source": "sources"}
LIMITS = {"core": (3, 3), "role": (3, 5), "task": (4, 6), "source": (0, 2)}
FORBIDDEN = [r"CPO Creativity", r"(?<![а-яА-Я])граф(?:и|ът|а|ове|овете)?(?![а-яА-Я])", r"knowledge graph"]


class BuildError(RuntimeError):
    pass


def validate(raw):
    eng = raw.get("engine")
    if eng not in AUTHORS:
        raise BuildError(f"unknown engine {eng!r}")
    ps = raw.get("protocols") or []
    ids = [p.get("id") for p in ps]
    if len(ids) != len(set(ids)):
        raise BuildError("duplicate ids")
    if not 10 <= len(ps) <= 14:
        raise BuildError(f"{len(ps)} protocols, expected 10..14")
    for kind, (lo, hi) in LIMITS.items():
        n = sum(p.get("kind") == kind for p in ps)
        if not lo <= n <= hi:
            raise BuildError(f"{n} {kind} protocols, expected {lo}..{hi}")
    for c in ("core-governance", "core-identity", "core-output"):
        if f"{eng}-{c}" not in ids:
            raise BuildError(f"missing {eng}-{c}")
    for p in ps:
        pid = p.get("id", "")
        if not re.fullmatch(rf"{re.escape(eng)}-[a-z0-9-]+", pid):
            raise BuildError(f"bad id {pid!r}")
        if p.get("kind") not in FOLDER:
            raise BuildError(f"bad kind in {pid}")
        for f in ("title", "summary", "when"):
            if not isinstance(p.get(f), str) or not p[f].strip():
                raise BuildError(f"{pid}: missing {f}")
        if not 4 <= len(p.get("rules", [])) <= 8:
            raise BuildError(f"{pid}: {len(p.get('rules', []))} rules, expected 4..8")
        if len(p.get("constraints", [])) < 2 or len(p.get("evaluation", [])) < 2:
            raise BuildError(f"{pid}: needs >=2 constraints and >=2 evaluation")
    if raw.get("default_task") not in ids or next(p for p in ps if p["id"] == raw["default_task"])["kind"] != "task":
        raise BuildError("default_task is not a task in the bank")
    roles = [p["id"] for p in ps if p["kind"] == "role"]
    dr = raw.get("default_roles") or []
    if not dr or any(r not in roles for r in dr) or not 1 <= len(dr) <= 5:
        raise BuildError("default_roles invalid")
    blob = json.dumps(raw, ensure_ascii=False)
    for pat in FORBIDDEN:
        m = re.search(pat, blob, re.I)
        if m:
            raise BuildError(f"forbidden term: {blob[max(0, m.start()-40):m.end()+40]!r}")
    return eng


def dump(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build(raw, date):
    eng = validate(raw)
    base = ROOT / eng
    bank = base / "protocol-bank"
    for k in FOLDER.values():
        d = bank / k
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("*.json"):
            old.unlink()
    order = {"core": 0, "role": 1, "task": 2, "source": 3}
    ps = sorted(raw["protocols"], key=lambda p: (order[p["kind"]], -int(p.get("priority", 0)), p["id"]))
    roles = [p["id"] for p in ps if p["kind"] == "role"]
    completer = raw["default_roles"][-1] if raw["default_roles"][-1] in roles else roles[-1]
    entries = []
    for p in ps:
        doc = {
            "id": p["id"], "title": p["title"], "summary": p["summary"], "version": "0.1.0",
            "rules": p["rules"], "constraints": p["constraints"], "evaluation": p["evaluation"],
            "protocol_schema": "creativity.ds-protocol/1.0", "kind": p["kind"], "status": "pilot",
            "engine": eng, "author_model": AUTHORS[eng],
            "origin_note": f"Creativity LTD kindergarten digital scientist competition ({date}); authored by {AUTHORS[eng]}, assembled by Claude; requires owner approval.",
        }
        rel = f"{FOLDER[p['kind']]}/{p['id']}.json"
        data = dump(doc)
        (bank / rel).write_bytes(data)
        entries.append({
            "id": p["id"], "kind": p["kind"], "title": p["title"], "path": rel, "version": "0.1.0",
            "status": "pilot", "select": "required" if p["kind"] == "core" else "selectable",
            "when": p["when"], "tags": p.get("tags", []), "priority": int(p.get("priority", 50)),
            "dependencies": [], "sha256": hashlib.sha256(data).hexdigest(),
        })
    manifest = {
        "manifest_schema": "creativity.ds-manifest/1.0",
        "project": f"Creativity Kindergarten Digital Scientist — {raw['system_name']}",
        "engine": eng,
        "system_name": raw["system_name"],
        "author_model": AUTHORS[eng],
        "version": "0.1.0",
        "release_status": "pilot",
        "owner": "Creativity LTD / Креативност ЕООД",
        "updated_on": date,
        "repository": REPO,
        "repository_prefix": f"kindergarten-ds/{eng}/protocol-bank",
        "compatibility": "Read access to public GitHub + Markdown instructions; optional Python 3.10+ resolver (kindergarten-ds/scripts/resolve_kg.py).",
        "visibility_note": "PUBLIC pilot layer for the kindergarten digital-scientist competition. No personal data of children, ever.",
        "execution_policy": {
            "git_snapshot": "Resolve default branch to full commit SHA once, and use only that SHA for all files.",
            "protocol_on_missing": "fail-closed; never substitute imagined contents",
            "required_protocols": [p["id"] for p in ps if p["kind"] == "core"],
            "priority": ["system/platform safety", "child protection and privacy", "explicit human constraints", "core protocols", "roles", "task", "sources"],
            "review_required": True,
            "default_task": raw["default_task"],
            "default_roles": raw["default_roles"],
            "completer_role": completer,
            "selection_limits": {"task": 1, "role_min": 1, "role_max": 5, "source": 2},
            "version_validation": "SHA-256 over UTF-8 raw bytes of each protocol JSON, then check id/version/kind/schema.",
        },
        "intake_questions": raw.get("intake_questions", [])[:3],
        "entries": entries,
    }
    (bank / "manifest.json").write_bytes(dump(manifest))
    write_skill(raw, eng, manifest)
    return eng, len(entries)


SKILL = """---
name: {name}
description: {desc}
---

# {system} — дигитален учен за детската градина

Автор на протоколите: **{author}** · Сглобено от Claude · Creativity LTD / Креативност ЕООД · pilot v0.1.0
Част от състезанието „Дигитален учен за детската градина“ (5 системи, 5 банки протоколи).

You are a SMALL ORCHESTRATOR. You hold no methodology yourself: every rule lives in this skill's own protocol bank on GitHub.
The teacher (and the group team) is the lead researcher and decides. You propose, check, explain and report.
Children aged 3–7 never use AI on their own through you, and no personal data of a child ever enters a prompt.

## 1. Intake — ask only what is missing (one message, max 3 questions)
{intake}

## 2. Load THIS engine's bank — never another one, never from memory
Manifest (engine `{engine}`):
`https://raw.githubusercontent.com/{repo}/main/kindergarten-ds/{engine}/protocol-bank/manifest.json`

1. Resolve `main` to ONE full commit SHA and read every file from that SHA
   (`https://raw.githubusercontent.com/{repo}/<SHA>/kindergarten-ds/{engine}/protocol-bank/<path>`).
   With Python: `python3 kindergarten-ds/scripts/resolve_kg.py --engine {engine} --question "..." --goal "..."`.
2. Load **all required core** protocols, **1–5 roles** (`{completer}` always last), **exactly 1 task**, **0–2 sources**.
   Choose by the request and each entry's `tags`, `when`, `priority`. Default task: `{task}`. Default roles: {roles}.
3. Check `id`, `version`, `kind` and SHA-256 against the manifest. Missing or mismatched mandatory file → stop and say so.
   Never invent protocol contents. Without GitHub access, say so and work only from an exported copy the human gives you.

## 3. Execute
Run the roles **in order**, each strictly within its protocol, under the three core protocols. Keep every [НЕПРОВЕРЕНО] marker through all steps.
If the request contains a child's name, photo, voice, health detail or anything identifying — stop and ask for an anonymised version first.

## 4. Report
Follow `{engine}-core-output`. Always finish with the teacher's decision point and a provenance block:
commit SHA · protocol IDs, versions, SHA-256 · what each role did · status `pilot — owner review required`.

## 5. Competition note
This skill may be run by any AI system. Do not borrow rules from other engines' banks; the comparison depends on each bank standing alone.
"""


def write_skill(raw, eng, manifest):
    name = "creativity-" + eng
    d = ROOT / eng / "skill" / name
    d.mkdir(parents=True, exist_ok=True)
    desc = raw["skill_description_en"].strip().replace("\n", " ")
    desc = f"Creativity LTD kindergarten digital scientist «{raw['system_name']}». " + desc
    desc = desc.replace(":", " —")[:1000]
    intake = "\n".join(f"{i}. {q}" for i, q in enumerate(manifest["intake_questions"], 1)) or "1. Какво искате да постигнете и за коя възрастова група?"
    pol = manifest["execution_policy"]
    (d / "SKILL.md").write_text(SKILL.format(
        name=name, desc=desc, system=raw["system_name"], author=AUTHORS[eng], intake=intake, engine=eng, repo=REPO,
        completer=pol["completer_role"], task=pol["default_task"], roles=", ".join(f"`{r}`" for r in pol["default_roles"]),
    ), encoding="utf-8")
    lines = [f"# {raw['system_name']} (`{eng}`)", "", f"Автор: {AUTHORS[eng]}", ""]
    if raw.get("system_overview"):
        lines += [raw["system_overview"].strip(), ""]
    if raw.get("example"):
        lines += ["## Пример", "", raw["example"].strip(), ""]
    lines += ["## Протоколи", "", "| ID | Вид | Заглавие |", "|---|---|---|"]
    lines += [f"| `{e['id']}` | {e['kind']} | {e['title']} |" for e in manifest["entries"]]
    (ROOT / eng / "SYSTEM.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("raw", nargs="+")
    ap.add_argument("--date", default="2026-11-16")
    a = ap.parse_args()
    ok = True
    for f in a.raw:
        try:
            eng, n = build(json.loads(Path(f).read_text(encoding="utf-8")), a.date)
            print(f"OK  {eng}: {n} protocols")
        except (BuildError, KeyError, ValueError) as e:
            ok = False
            print(f"ERR {f}: {e}", file=sys.stderr)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
