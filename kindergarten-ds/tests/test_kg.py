import argparse, hashlib, json, sys, tempfile, shutil, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import resolve_kg as R

ENGINES = R.ENGINES


def args(engine, **kw):
    a = dict(engine=engine, question="Искам игра за есента за 4-годишни", goal="план", intent="", language="bg",
             deliverable="report", task=None, roles=None, sources=None, local=str(ROOT / engine / "protocol-bank"), ref=None)
    a.update(kw)
    return argparse.Namespace(**a)


class KindergartenBanks(unittest.TestCase):
    def test_every_engine_has_bank_and_skill(self):
        for e in ENGINES:
            self.assertTrue((ROOT / e / "protocol-bank" / "manifest.json").exists(), e)
            skill = ROOT / e / "skill" / f"creativity-{e}" / "SKILL.md"
            self.assertTrue(skill.exists(), e)
            text = skill.read_text(encoding="utf-8")
            self.assertIn(f"kindergarten-ds/{e}/protocol-bank/manifest.json", text)
            for other in ENGINES:
                if other != e:
                    self.assertNotIn(f"kindergarten-ds/{other}/", text, f"{e} skill points to {other}")

    def test_hashes_ids_and_engine_isolation(self):
        for e in ENGINES:
            m = json.loads((ROOT / e / "protocol-bank" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(m["engine"], e)
            ids = [x["id"] for x in m["entries"]]
            self.assertEqual(len(ids), len(set(ids)))
            for x in m["entries"]:
                self.assertTrue(x["id"].startswith(e + "-"))
                raw = (ROOT / e / "protocol-bank" / x["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), x["sha256"])

    def test_resolution_core_first_completer_last(self):
        for e in ENGINES:
            run = R.resolve(args(e))
            ids = [p["id"] for p in run["selected_protocols"]]
            self.assertEqual(ids[:3], [f"{e}-core-governance", f"{e}-core-identity", f"{e}-core-output"])
            m = json.loads((ROOT / e / "protocol-bank" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(run["role_order"][-1], m["execution_policy"]["completer_role"])
            self.assertEqual(sum(p["kind"] == "task" for p in run["selected_protocols"]), 1)

    def test_wrong_engine_manifest_rejected(self):
        with self.assertRaises(R.ProtocolError):
            R.resolve(args("kg-play-design", local=str(ROOT / "kg-ai-guardian" / "protocol-bank")))

    def test_unknown_ids_fail_closed(self):
        with self.assertRaises(R.ProtocolError):
            R.resolve(args("kg-ai-guardian", task="kg-ai-guardian-task-fictitious"))

    def test_tampered_protocol_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "bank"
            shutil.copytree(ROOT / "kg-evidence-lab" / "protocol-bank", dst)
            f = dst / "core" / "kg-evidence-lab-core-governance.json"
            obj = json.loads(f.read_text(encoding="utf-8"))
            obj["rules"].append("Injected rule")
            f.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(R.ProtocolError):
                R.resolve(args("kg-evidence-lab", local=str(dst)))


if __name__ == "__main__":
    unittest.main()
