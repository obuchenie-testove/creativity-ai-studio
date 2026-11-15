#!/usr/bin/env python3
"""Resolve one version-pinned, hash-verified Creativity presentation context.

Standard library only. The resolver is deterministic: it never generates slides.

Sources, in order:
  1. GitHub   - default branch -> full commit SHA (api.github.com), files from
                raw.githubusercontent.com at that SHA, falling back to the
                jsDelivr mirror of the same SHA when raw is blocked.
  2. --local  - an exported copy of protocol-bank/ (offline). Pass
                --snapshot-commit <sha> so the report names the real commit;
                otherwise the run is labelled "unverified-local".
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path, PurePosixPath

REPO = "obuchenie-testove/creativity-ai-studio"
PREFIX = "presentation-protocol-engine/protocol-bank"
MANIFEST_SCHEMA = "creativity.presentation-manifest/1.0"
PROTOCOL_SCHEMA = "creativity.presentation-protocol/1.0"
KINDS = ("core", "presentation", "visual", "thinking")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
WORD_RE = re.compile(r"\w+", re.UNICODE)
USER_AGENT = "Creativity-Presentation-Resolver/0.2"


class ProtocolError(RuntimeError):
    """Any condition under which the run must fail closed."""


# --------------------------------------------------------------------------- fetch

def get_url(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read()


def raw_url(sha, path):
    return f"https://raw.githubusercontent.com/{REPO}/{sha}/{PREFIX}/{path}"


def jsdelivr_url(sha, path):
    return f"https://cdn.jsdelivr.net/gh/{REPO}@{sha}/{PREFIX}/{path}"


def resolve_head(fetch):
    """Default branch -> full commit SHA, using the GitHub API."""
    try:
        repo = json.loads(fetch(f"https://api.github.com/repos/{REPO}"))
        branch = repo.get("default_branch") or "main"
        head = json.loads(fetch(f"https://api.github.com/repos/{REPO}/commits/{branch}"))
    except (OSError, ValueError) as exc:
        raise ProtocolError(f"Cannot read the current commit from GitHub API: {exc}") from exc
    return head.get("sha"), branch


class Snapshot:
    """One immutable view of the protocol bank."""

    def __init__(self, commit, source, reader):
        self.commit = commit
        self.source = source
        self._reader = reader

    def read(self, path):
        try:
            return self._reader(path)
        except ProtocolError:
            raise
        except (OSError, ValueError) as exc:
            raise ProtocolError(f"Cannot read {path}: {exc}") from exc


def open_snapshot(local=None, ref=None, snapshot_commit=None, fetch=get_url):
    if local:
        root = Path(local).resolve()
        if snapshot_commit:
            commit = snapshot_commit.lower()
            if not SHA_RE.match(commit):
                raise ProtocolError("--snapshot-commit must be a full 40-character Git SHA")
        else:
            commit = "unverified-local"
        return Snapshot(commit, "local", lambda path: (root / path).read_bytes())

    branch = None
    if ref is None:
        ref, branch = resolve_head(fetch)
    ref = (ref or "").lower()
    if not SHA_RE.match(ref):
        raise ProtocolError("Cannot resolve a valid immutable Git commit SHA")

    state = {"source": None}

    def reader(path):
        errors = []
        order = [("github-raw", raw_url), ("jsdelivr", jsdelivr_url)]
        if state["source"] == "jsdelivr":
            order.reverse()
        for name, build in order:
            try:
                data = fetch(build(ref, path))
                state["source"] = state["source"] or name
                return data
            except (OSError, ValueError) as exc:
                errors.append(f"{name}: {exc}")
        raise ProtocolError(f"Cannot read {path} at {ref} ({'; '.join(errors)})")

    snap = Snapshot(ref, None, reader)
    snap.branch = branch
    snap.state = state
    return snap


# ------------------------------------------------------------------- validation

def read_json(data, label):
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProtocolError(f"Invalid JSON in {label}: {exc}") from exc


def safe_path(entry):
    raw = entry.get("path", "")
    p = PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts or not raw.endswith(".json") or p.parts[0] != entry.get("kind"):
        raise ProtocolError(f"Unsafe or unexpected path for {entry.get('id')}: {raw!r}")
    return raw


def validate_manifest(manifest):
    if manifest.get("manifest_schema") != MANIFEST_SCHEMA:
        raise ProtocolError("Unsupported manifest schema")
    entries = manifest.get("entries")
    policy = manifest.get("execution_policy")
    if not isinstance(entries, list) or not isinstance(policy, dict):
        raise ProtocolError("Manifest must contain 'entries' and 'execution_policy'")
    index = {}
    for e in entries:
        for key in ("id", "kind", "version", "path", "sha256", "status"):
            if key not in e:
                raise ProtocolError(f"Manifest entry is missing '{key}': {e.get('id', e)}")
        if e["kind"] not in KINDS:
            raise ProtocolError(f"Unknown kind for {e['id']}: {e['kind']}")
        if e["id"] in index:
            raise ProtocolError("Duplicate protocol IDs")
        safe_path(e)
        index[e["id"]] = e

    allowed = set(policy.get("allowed_status", ["pilot", "approved"]))
    required = policy.get("required_protocols") or []
    core_ids = {e["id"] for e in entries if e["kind"] == "core"}
    if not required:
        raise ProtocolError("execution_policy.required_protocols is empty")
    for pid in required:
        e = index.get(pid)
        if e is None:
            raise ProtocolError(f"Required protocol is missing from the manifest: {pid}")
        if e["kind"] != "core":
            raise ProtocolError(f"Required protocol is not a core protocol: {pid}")
    missing_core = core_ids - set(required)
    if missing_core:
        raise ProtocolError(f"Core protocols not listed as required: {sorted(missing_core)}")
    for kind in ("presentation", "visual"):
        did = policy.get(f"default_{kind}")
        if did not in index or index[did]["kind"] != kind:
            raise ProtocolError(f"default_{kind} is missing or not a {kind} protocol: {did}")
    return index, policy, allowed


# -------------------------------------------------------------------- selection

def words(text):
    return WORD_RE.findall(text.lower())


def word_matches(text_word, tag_word):
    if tag_word.isascii():
        return text_word in (tag_word, tag_word + "s", tag_word + "es")
    # Cyrillic and other scripts: inflections are suffixes, so a word that
    # starts with the tag word matches ("данни" -> "данните"), but a tag inside
    # a longer word does not ("история" does not match "предистория").
    return text_word.startswith(tag_word)


def tag_in(tag, text_words):
    tw = words(tag)
    if not tw:
        return False
    for i in range(len(text_words) - len(tw) + 1):
        if all(word_matches(text_words[i + j], tw[j]) for j in range(len(tw))):
            return True
    return False


def score(entry, text_words):
    return [t for t in entry.get("tags", []) if tag_in(t, text_words)]


def pick(entries, kind, text, explicit=None, default=None, allowed=None):
    """Return (entry or None, selection record)."""
    choices = [e for e in entries if e["kind"] == kind]
    if explicit and explicit != "auto":
        match = [e for e in choices if e["id"] == explicit]
        if not match:
            raise ProtocolError(f"Unknown {kind} protocol ID: {explicit}")
        return match[0], {"method": "explicit"}
    if allowed is not None:
        choices = [e for e in choices if e["status"] in allowed]
    text_words = words(text)
    scored = []
    for e in choices:
        hits = score(e, text_words)
        if hits:
            scored.append((len(hits), e.get("priority", 0), e["id"], e, hits))
    if not scored:
        if default is None:
            return None, {"method": "none-matched"}
        entry = next(e for e in entries if e["id"] == default)
        return entry, {"method": "default", "note": "no tag matched the brief"}
    scored.sort(key=lambda a: (-a[0], -a[1], a[2]))
    best = scored[0]
    tied = [s[2] for s in scored if s[0] == best[0] and s[1] == best[1]]
    record = {"method": "tags", "matched_tags": best[4], "score": best[0]}
    if len(tied) > 1:
        record["ambiguous_with"] = [t for t in tied if t != best[2]]
        record["note"] = "tie broken by ID order; host AI should confirm the choice by meaning"
    return best[3], record


# ---------------------------------------------------------------------- resolve

def compatibility_warnings(selected, args):
    warnings = []
    ids = {p["id"] for p in selected}
    if "present-pechakucha" in ids and args.slides and args.slides != 20:
        warnings.append(f"present-pechakucha requires exactly 20 slides; brief asks for {args.slides}")
    return warnings


def resolve(args, fetch=get_url):
    snap = open_snapshot(args.local, args.ref, getattr(args, "snapshot_commit", None), fetch)
    manifest_raw = snap.read("manifest.json")
    manifest = read_json(manifest_raw, "manifest.json")
    index, policy, allowed = validate_manifest(manifest)
    entries = manifest["entries"]

    text = " ".join(x or "" for x in (args.topic, args.goal, args.audience, args.intent, args.visual_hint))
    plan = [(pid, {"method": "required"}) for pid in policy["required_protocols"]]
    for kind, explicit in (("presentation", args.presentation), ("visual", args.visual)):
        entry, rec = pick(entries, kind, text, explicit, policy[f"default_{kind}"], allowed)
        plan.append((entry["id"], rec))
    if args.thinking:
        entry, rec = pick(entries, "thinking", text, args.thinking, None, allowed)
        if entry is not None:
            plan.append((entry["id"], rec))

    loaded = []
    for pid, rec in plan:
        entry = index[pid]
        if entry["status"] not in allowed:
            raise ProtocolError(f"Protocol {pid} has status '{entry['status']}', not in {sorted(allowed)}")
        raw = snap.read(entry["path"])
        digest = hashlib.sha256(raw).hexdigest()
        if digest != entry["sha256"]:
            raise ProtocolError(f"SHA256 mismatch for {pid}")
        item = read_json(raw, entry["path"])
        if (item.get("id") != pid or item.get("version") != entry["version"]
                or item.get("kind") != entry["kind"] or item.get("protocol_schema") != PROTOCOL_SCHEMA):
            raise ProtocolError(f"Protocol metadata mismatch for {pid}")
        loaded.append({"id": pid, "version": entry["version"], "sha256": digest, "kind": entry["kind"],
                       "status": entry["status"], "selection": rec, "content": item})

    source = snap.source or snap.state["source"]
    return {
        "status": "pilot-needs-expert-review",
        "source_repository": REPO,
        "git_commit": snap.commit,
        "source": source,
        "bank_version": manifest.get("version"),
        "bank_digest": hashlib.sha256(manifest_raw).hexdigest(),
        "brief": {"topic": args.topic, "goal": args.goal, "audience": args.audience, "minutes": args.minutes,
                  "slides": args.slides, "format": args.format, "language": args.language},
        "selected_protocols": loaded,
        "warnings": compatibility_warnings(loaded, args),
        "validation": {
            "manifest": "ok",
            "hashes": "ok",
            "hash_verified_by": "resolve.py",
            "conflicts": "not-detected-automatically; host AI must check using the manifest priority order",
            "rendered_file": "not-created-by-resolver",
        },
        "next_step": "Host AI applies the protocols, builds the slide plan or file, evaluates it and reports provenance.",
    }


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--topic", required=True)
    p.add_argument("--goal", required=True)
    p.add_argument("--audience", required=True)
    p.add_argument("--minutes", type=int, default=15)
    p.add_argument("--slides", type=int, default=None)
    p.add_argument("--language", default="bg")
    p.add_argument("--format", default="outline")
    p.add_argument("--intent", default="")
    p.add_argument("--visual-hint", default="")
    p.add_argument("--presentation", help="Explicit presentation protocol ID")
    p.add_argument("--visual", help="Explicit visual protocol ID")
    p.add_argument("--thinking", help="Thinking protocol ID, or 'auto' to select by tags")
    p.add_argument("--local", help="Local protocol-bank directory (offline snapshot)")
    p.add_argument("--snapshot-commit", help="Git commit SHA that the local snapshot was exported from")
    p.add_argument("--ref", help="Fixed Git commit SHA; omit to resolve the default branch")
    p.add_argument("--output", default="-")
    return p


def main():
    args = build_parser().parse_args()
    try:
        result = resolve(args)
    except ProtocolError as exc:
        print("PROTOCOL RESOLUTION FAILED: " + str(exc), file=sys.stderr)
        sys.exit(2)
    value = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output == "-":
        print(value, end="")
    else:
        Path(args.output).write_text(value, encoding="utf-8")


if __name__ == "__main__":
    main()
