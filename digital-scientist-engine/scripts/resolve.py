#!/usr/bin/env python3
"""Resolve one version-pinned, hash-verified Creativity Digital Scientist context. Stdlib only.

Loads: all required core protocols + 1..5 roles + exactly 1 task + 0..2 source protocols,
from ONE immutable Git commit, and verifies every file against the manifest SHA-256.
"""
import argparse, hashlib, json, re, sys, urllib.request
from pathlib import Path

REPO = "obuchenie-testove/creativity-ai-studio"
PREFIX = "digital-scientist-engine/protocol-bank"
HEAD_API = f"https://api.github.com/repos/{REPO}/commits/main"
MANIFEST_SCHEMA = "creativity.ds-manifest/1.0"
PROTOCOL_SCHEMA = "creativity.ds-protocol/1.0"


class ProtocolError(RuntimeError):
    pass


def get_url(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "Creativity-DS-Resolver/0.1"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read()


def snapshot(local=None, ref=None, fetch=get_url):
    if local:
        root = Path(local)
        return "LOCAL-TEST-SNAPSHOT", lambda path: (root / path).read_bytes()
    if ref is None:
        ref = json.loads(fetch(HEAD_API)).get("sha")
    if not ref or len(ref) != 40 or any(c not in "0123456789abcdef" for c in ref.lower()):
        raise ProtocolError("Cannot resolve a valid immutable Git commit SHA")
    return ref, lambda path: fetch(f"https://raw.githubusercontent.com/{REPO}/{ref}/{PREFIX}/{path}")


def score(entry, text):
    words = text.lower()
    hits = 0
    for t in entry.get("tags", []):
        t = t.lower()
        if t.isascii():
            hits += bool(re.search(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])", words))
        else:
            hits += t in words
    return hits


def pick_one(entries, kind, text, explicit, default):
    choices = [e for e in entries if e["kind"] == kind]
    if explicit:
        match = [e for e in choices if e["id"] == explicit]
        if not match:
            raise ProtocolError(f"Unknown {kind} protocol ID: {explicit}")
        return match[0]
    scored = sorted(((score(e, text), e.get("priority", 0), e["id"], e) for e in choices if score(e, text)), key=lambda a: (-a[0], -a[1], a[2]))
    if scored:
        return scored[0][3]
    return next(e for e in choices if e["id"] == default)


def pick_roles(entries, text, explicit, defaults, limits):
    roles = {e["id"]: e for e in entries if e["kind"] == "role"}
    if explicit:
        ids = [x.strip() for x in explicit.split(",") if x.strip()]
        for rid in ids:
            if rid not in roles:
                raise ProtocolError("Unknown role protocol ID: " + rid)
    else:
        ids = list(defaults)
        extra = sorted((score(e, text), e.get("priority", 0), rid) for rid, e in roles.items() if rid not in ids and score(e, text))
        for _, _, rid in sorted(extra, key=lambda a: (-a[0], -a[1], a[2])):
            ids.insert(-1, rid)  # keep the completer last
    if "role-completer" in ids:
        ids = [r for r in ids if r != "role-completer"] + ["role-completer"]
    if not limits["role_min"] <= len(ids) <= limits["role_max"]:
        raise ProtocolError(f"Role count {len(ids)} outside {limits['role_min']}..{limits['role_max']}")
    return ids


def resolve(args, fetch=get_url):
    sha, load = snapshot(args.local, args.ref, fetch)
    manifest = json.loads(load("manifest.json").decode("utf-8"))
    if manifest.get("manifest_schema") != MANIFEST_SCHEMA:
        raise ProtocolError("Unsupported manifest schema")
    entries = manifest["entries"]
    index = {e["id"]: e for e in entries}
    if len(index) != len(entries):
        raise ProtocolError("Duplicate protocol IDs")
    policy = manifest["execution_policy"]
    text = " ".join([args.question, args.goal, args.intent or ""])

    wanted = list(policy["required_protocols"])
    wanted += pick_roles(entries, text, args.roles, policy["default_roles"], policy["selection_limits"])
    wanted.append(pick_one(entries, "task", text, args.task, policy["default_task"])["id"])
    if args.sources:
        srcs = [s.strip() for s in args.sources.split(",") if s.strip()]
        if len(srcs) > policy["selection_limits"]["source"]:
            raise ProtocolError("Too many source protocols")
        for s in srcs:
            if s not in index or index[s]["kind"] != "source":
                raise ProtocolError("Unknown source protocol ID: " + s)
        wanted += srcs

    loaded = []
    for pid in wanted:
        entry = index[pid]
        raw = load(entry["path"])
        digest = hashlib.sha256(raw).hexdigest()
        if digest != entry["sha256"]:
            raise ProtocolError("SHA256 mismatch for " + pid)
        item = json.loads(raw.decode("utf-8"))
        if item.get("id") != pid or item.get("version") != entry["version"] or item.get("kind") != entry["kind"] or item.get("protocol_schema") != PROTOCOL_SCHEMA:
            raise ProtocolError("Protocol metadata mismatch for " + pid)
        loaded.append({"id": pid, "version": entry["version"], "sha256": digest, "kind": entry["kind"], "status": entry["status"], "content": item})

    return {
        "status": "pilot-needs-owner-review",
        "source_repository": REPO,
        "git_commit": sha,
        "brief": {"question": args.question, "goal": args.goal, "language": args.language, "deliverable": args.deliverable},
        "selected_protocols": loaded,
        "role_order": [p["id"] for p in loaded if p["kind"] == "role"],
        "validation": {"manifest": "ok", "hashes": "ok", "conflicts": "needs-review-by-agent", "external_sources": "not-queried-by-resolver"},
        "next_step": "Host AI runs the roles in order under core protocols, executes the task, then reports with core-output.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--question", required=True, help="Research question or task in plain language")
    p.add_argument("--goal", required=True, help="What the human needs at the end")
    p.add_argument("--intent", default="")
    p.add_argument("--language", default="bg")
    p.add_argument("--deliverable", default="report")
    p.add_argument("--task", help="Explicit task protocol ID")
    p.add_argument("--roles", help="Comma-separated role IDs (1..5)")
    p.add_argument("--sources", help="Comma-separated source protocol IDs (0..2)")
    p.add_argument("--local", help="Local protocol-bank directory (tests/offline snapshot)")
    p.add_argument("--ref", help="Fixed Git commit SHA; omit to resolve current main")
    p.add_argument("--output", default="-")
    a = p.parse_args()
    try:
        result = resolve(a)
    except (ProtocolError, OSError, ValueError, KeyError) as exc:
        print("PROTOCOL RESOLUTION FAILED: " + str(exc), file=sys.stderr)
        sys.exit(2)
    value = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if a.output == "-":
        print(value, end="")
    else:
        Path(a.output).write_text(value, encoding="utf-8")


if __name__ == "__main__":
    main()
