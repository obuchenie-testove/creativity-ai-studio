#!/usr/bin/env python3
"""After editing protocol JSON files, sync manifest.json with them.

For every manifest entry, copies the file's `version` and recomputes `sha256`.
Refuses to continue if a file's content changed but its `version` did not,
so every published change gets a new protocol version.

Usage:
  python scripts/sync_manifest.py           # update manifest.json, then rebuild BUNDLE.md
  python scripts/sync_manifest.py --check   # report what would change, write nothing
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "protocol-bank" / "manifest.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changed, errors = [], []
    for e in manifest["entries"]:
        raw = (MANIFEST.parent / e["path"]).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        version = json.loads(raw)["version"]
        if digest == e["sha256"]:
            continue
        if version == e["version"]:
            errors.append(f"{e['id']}: content changed but version is still {version}; bump the version in the file")
            continue
        changed.append(f"{e['id']}: {e['version']} -> {version}")
        e["version"], e["sha256"] = version, digest
    for line in errors:
        print("ERROR " + line, file=sys.stderr)
    for line in changed:
        print("UPDATE " + line)
    if errors:
        sys.exit(1)
    if not changed:
        print("manifest.json is in sync")
        return
    if args.check:
        sys.exit(1)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_bundle.py")], check=True)
    print("Now bump manifest 'version' if this is a new bank release, rebuild the bundle, commit, and tag bank-v<version>.")


if __name__ == "__main__":
    main()
