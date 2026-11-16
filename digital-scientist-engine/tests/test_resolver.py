import argparse, hashlib, json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import resolve

ROOT = Path(__file__).resolve().parents[1] / "protocol-bank"


def arguments(**kwargs):
    a = dict(question="Какво се знае за AI в образованието?", goal="кратък преглед", intent="", language="bg",
             deliverable="report", task=None, roles=None, sources=None, local=str(ROOT), ref=None)
    a.update(kwargs)
    return argparse.Namespace(**a)


class ResolverTest(unittest.TestCase):
    def test_manifest_hashes_and_unique_ids(self):
        m = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        ids = [e["id"] for e in m["entries"]]
        self.assertEqual(len(ids), len(set(ids)))
        for e in m["entries"]:
            self.assertEqual(hashlib.sha256((ROOT / e["path"]).read_bytes()).hexdigest(), e["sha256"])

    def test_core_always_first(self):
        run = resolve.resolve(arguments())
        self.assertEqual([p["id"] for p in run["selected_protocols"]][:3], ["core-governance", "core-identity", "core-output"])
        self.assertEqual(run["git_commit"], "LOCAL-TEST-SNAPSHOT")

    def test_auto_task_selection(self):
        run = resolve.resolve(arguments(question="Напиши статия за поредицата", goal="статия"))
        self.assertIn("task-series-article", [p["id"] for p in run["selected_protocols"]])

    def test_completer_is_last_role(self):
        run = resolve.resolve(arguments(roles="role-completer,role-explorer,role-evaluator"))
        self.assertEqual(run["role_order"][-1], "role-completer")

    def test_explicit_sources(self):
        run = resolve.resolve(arguments(sources="source-scholarly-mcp"))
        self.assertEqual(run["selected_protocols"][-1]["id"], "source-scholarly-mcp")

    def test_unknown_ids_fail_closed(self):
        with self.assertRaises(resolve.ProtocolError):
            resolve.resolve(arguments(task="task-fictitious"))
        with self.assertRaises(resolve.ProtocolError):
            resolve.resolve(arguments(roles="role-fictitious"))

    def test_tampered_protocol_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            m = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
            for e in m["entries"]:
                dest = root / e["path"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((ROOT / e["path"]).read_bytes())
            (root / "manifest.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
            target = root / "core/core-governance.json"
            obj = json.loads(target.read_text(encoding="utf-8"))
            obj["rules"].append("Injected rule")
            target.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(resolve.ProtocolError):
                resolve.resolve(arguments(local=str(root)))


if __name__ == "__main__":
    unittest.main()
