import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT / "skills" / "creativity-presentation-orchestrator" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import resolve  # noqa: E402

ROOT = PROJECT / "protocol-bank"
SHA = "6e6bfd7dbd9fc1ef9d274e2a06c897456034b58c"


def arguments(**kwargs):
    a = dict(topic="How our AI teams work", goal="Get decision on a new operating model", audience="leadership",
             minutes=15, slides=10, language="bg", format="outline", intent="", visual_hint="",
             presentation=None, visual=None, thinking=None, local=str(ROOT), ref=None, snapshot_commit=None)
    a.update(kwargs)
    return argparse.Namespace(**a)


def ids(run):
    return [p["id"] for p in run["selected_protocols"]]


class BankCopy:
    """Temporary copy of the protocol bank that a test may mutate."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "bank"
        shutil.copytree(ROOT, self.root)
        self.manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        return self

    def entry(self, pid):
        return next(e for e in self.manifest["entries"] if e["id"] == pid)

    def save(self):
        (self.root / "manifest.json").write_text(json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")

    def __exit__(self, *exc):
        self.tmp.cleanup()


class ManifestTest(unittest.TestCase):
    def test_manifest_hashes_unique_ids_and_no_orphans(self):
        m = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        ids_ = [e["id"] for e in m["entries"]]
        self.assertEqual(len(ids_), len(set(ids_)))
        for e in m["entries"]:
            self.assertEqual(hashlib.sha256((ROOT / e["path"]).read_bytes()).hexdigest(), e["sha256"])
        on_disk = {str(p.relative_to(ROOT)) for p in ROOT.glob("*/*.json")}
        self.assertEqual(on_disk, {e["path"] for e in m["entries"]})

    def test_protocol_files_match_manifest_metadata(self):
        m = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        for e in m["entries"]:
            item = json.loads((ROOT / e["path"]).read_text(encoding="utf-8"))
            self.assertEqual((item["id"], item["version"], item["kind"]), (e["id"], e["version"], e["kind"]))
            self.assertEqual(item["protocol_schema"], resolve.PROTOCOL_SCHEMA)

    def test_bundle_is_up_to_date(self):
        result = subprocess.run([sys.executable, str(PROJECT / "scripts" / "build_bundle.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class SelectionTest(unittest.TestCase):
    """Golden set: bilingual briefs -> expected presentation / visual protocol."""

    GOLDEN = [
        # (topic, goal, audience, presentation, visual)
        ("ИИ в образованието", "учениците да разберат възможности, ограничения и отговорна употреба", "Ученици",
         "present-bildungsansatz", "visual-infographic-educational"),
        ("Изкуствен интелект в училище", "Да разберат как да го използват отговорно", "Учители",
         "present-bildungsansatz", None),
        ("AI in education", "students understand limits and responsible use", "students",
         "present-bildungsansatz", "visual-infographic-educational"),
        ("Lecture on photosynthesis", "pupils learn", "7th graders", "present-bildungsansatz", None),
        ("Investor pitch for a technology startup", "Secure seed funding", "executives and investors",
         "present-pitch", "visual-tech-futuristic"),
        ("Представяне на стартъп пред инвеститори", "Да получим финансиране", "Инвеститори", "present-pitch", None),
        ("Резултати от изследване", "Да представим резултатите, източници и ограничения", "Университетска аудитория",
         "present-scientific", "visual-academic-research"),
        ("Research results", "Present findings with sources and limitations", "university audience",
         "present-scientific", "visual-academic-research"),
        ("Годишен отчет на компанията", "Представяне на данни и KPI", "Управителен съвет",
         "present-data-driven", "visual-precise"),
        ("Annual report", "Present KPIs", "Board of directors", "present-report", None),
        ("AI workshop за учители", "практическо обучение", "учители", "present-workshop", "visual-interactive-learning"),
        ("Възраждането и Паисий Хилендарски", "исторически контекст", "ученици 7 клас",
         "present-bildungsansatz", "visual-heritage-historical"),
        ("New product strategy", "Get a decision", "executive board", "present-classic-business", None),
    ]

    def test_golden_set(self):
        for topic, goal, audience, pres, vis in self.GOLDEN:
            with self.subTest(topic=topic):
                run = resolve.resolve(arguments(topic=topic, goal=goal, audience=audience))
                self.assertEqual(ids(run)[3], pres)
                if vis:
                    self.assertEqual(ids(run)[4], vis)

    def test_cyrillic_tag_inside_longer_word_does_not_match(self):
        run = resolve.resolve(arguments(topic="Предистория на компанията", goal="Да се разбере", audience="Служители"))
        self.assertNotEqual(ids(run)[3], "present-storytelling")

    def test_cyrillic_inflection_matches(self):
        self.assertTrue(resolve.tag_in("данни", resolve.words("анализ на данните")))
        self.assertTrue(resolve.tag_in("учител", resolve.words("за учителите")))

    def test_ascii_tag_is_whole_word(self):
        self.assertFalse(resolve.tag_in("ai", resolve.words("our aim")))
        self.assertTrue(resolve.tag_in("investor", resolve.words("for investors")))

    def test_default_when_nothing_matches(self):
        run = resolve.resolve(arguments(topic="xyz", goal="qqq", audience="zzz"))
        self.assertEqual(ids(run)[3:5], ["present-classic-business", "visual-clean"])
        self.assertEqual(run["selected_protocols"][3]["selection"]["method"], "default")

    def test_ties_are_reported(self):
        run = resolve.resolve(arguments(topic="Annual report", goal="Present KPIs", audience="Board of directors"))
        self.assertIn("ambiguous_with", run["selected_protocols"][4]["selection"])

    def test_thinking_auto_and_none(self):
        run = resolve.resolve(arguments(topic="Research results", goal="sources and limitations",
                                        audience="university", thinking="auto"))
        self.assertEqual(ids(run)[-1], "think-evidence")
        self.assertEqual(len(resolve.resolve(arguments())["selected_protocols"]), 5)

    def test_incompatible_slide_count_warns(self):
        run = resolve.resolve(arguments(presentation="present-pechakucha", slides=12))
        self.assertTrue(run["warnings"])


class ExplicitSelectionTest(unittest.TestCase):
    def test_explicit_selection(self):
        run = resolve.resolve(arguments(presentation="present-storytelling", visual="visual-editorial",
                                        thinking="think-systems"))
        self.assertEqual(ids(run)[-3:], ["present-storytelling", "visual-editorial", "think-systems"])

    def test_unknown_or_wrong_kind_id_fails_closed(self):
        for kw in ({"presentation": "present-fictitious"}, {"visual": "visual-nope"},
                   {"thinking": "think-nope"}, {"presentation": "visual-clean"}):
            with self.subTest(**kw), self.assertRaises(resolve.ProtocolError):
                resolve.resolve(arguments(**kw))


class ProvenanceTest(unittest.TestCase):
    def test_local_without_commit_is_unverified(self):
        run = resolve.resolve(arguments())
        self.assertEqual(run["git_commit"], "unverified-local")
        self.assertEqual(run["source"], "local")
        self.assertEqual(run["bank_digest"], hashlib.sha256((ROOT / "manifest.json").read_bytes()).hexdigest())
        self.assertEqual(run["validation"]["hash_verified_by"], "resolve.py")

    def test_local_with_snapshot_commit(self):
        self.assertEqual(resolve.resolve(arguments(snapshot_commit=SHA))["git_commit"], SHA)
        with self.assertRaises(resolve.ProtocolError):
            resolve.resolve(arguments(snapshot_commit="LOCAL-TEST"))

    def _fake_github(self, block_raw=False, sha=SHA):
        calls = []

        def fetch(url):
            calls.append(url)
            if url.endswith(f"/repos/{resolve.REPO}"):
                return json.dumps({"default_branch": "main"}).encode()
            if "/commits/" in url:
                return json.dumps({"sha": sha}).encode()
            if block_raw and "raw.githubusercontent.com" in url:
                raise OSError("PERMISSION_DENIED")
            rel = url.split("/protocol-bank/")[1]
            return (ROOT / rel).read_bytes()
        return fetch, calls

    def test_live_mode_pins_one_commit(self):
        fetch, calls = self._fake_github()
        run = resolve.resolve(arguments(local=None), fetch=fetch)
        self.assertEqual(run["git_commit"], SHA)
        self.assertEqual(run["source"], "github-raw")
        file_urls = [u for u in calls if "protocol-bank" in u]
        self.assertTrue(file_urls and all(f"/{SHA}/" in u for u in file_urls))

    def test_live_mode_falls_back_to_jsdelivr(self):
        fetch, calls = self._fake_github(block_raw=True)
        run = resolve.resolve(arguments(local=None), fetch=fetch)
        self.assertEqual(run["source"], "jsdelivr")
        self.assertTrue(any(f"cdn.jsdelivr.net/gh/{resolve.REPO}@{SHA}/" in u for u in calls))

    def test_invalid_head_sha_fails(self):
        fetch, _ = self._fake_github(sha="main")
        with self.assertRaises(resolve.ProtocolError):
            resolve.resolve(arguments(local=None), fetch=fetch)

    def test_github_unreachable_fails_closed(self):
        def down(url):
            raise OSError("blocked")
        with self.assertRaises(resolve.ProtocolError):
            resolve.resolve(arguments(local=None), fetch=down)


class FailClosedTest(unittest.TestCase):
    def test_change_requires_manifest_hash_update(self):
        with BankCopy() as b:
            target = b.root / "presentation/present-pitch.json"
            obj = json.loads(target.read_text(encoding="utf-8"))
            obj["rules"].append("New live external rule")
            target.write_text(json.dumps(obj), encoding="utf-8")
            b.save()
            with self.assertRaises(resolve.ProtocolError):
                resolve.resolve(arguments(local=str(b.root), presentation="present-pitch"))
            obj["version"] = "0.1.1"
            target.write_text(json.dumps(obj), encoding="utf-8")
            b.entry("present-pitch").update(version="0.1.1", sha256=hashlib.sha256(target.read_bytes()).hexdigest())
            b.save()
            run = resolve.resolve(arguments(local=str(b.root), presentation="present-pitch"))
            self.assertEqual(run["selected_protocols"][3]["version"], "0.1.1")
            self.assertIn("New live external rule", run["selected_protocols"][3]["content"]["rules"])

    def assert_fails(self, mutate, **kw):
        with BankCopy() as b:
            mutate(b)
            b.save()
            with self.assertRaises(resolve.ProtocolError):
                resolve.resolve(arguments(local=str(b.root), **kw))

    def test_missing_file(self):
        self.assert_fails(lambda b: (b.root / "core/core-governance.json").unlink())

    def test_invalid_json(self):
        def m(b):
            (b.root / "core/core-output.json").write_text("{bad")
            b.entry("core-output")["sha256"] = hashlib.sha256(b"{bad").hexdigest()
        self.assert_fails(m)

    def test_duplicate_id(self):
        self.assert_fails(lambda b: b.manifest["entries"].append(dict(b.entry("visual-clean"))))

    def test_incompatible_protocol_schema(self):
        def m(b):
            f = b.root / "core/core-quality.json"
            o = json.loads(f.read_text(encoding="utf-8"))
            o["protocol_schema"] = "creativity.presentation-protocol/2.0"
            f.write_text(json.dumps(o))
            b.entry("core-quality")["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
        self.assert_fails(m)

    def test_unsupported_manifest_schema(self):
        self.assert_fails(lambda b: b.manifest.update(manifest_schema="creativity.presentation-manifest/2.0"))

    def test_missing_core_entry(self):
        self.assert_fails(lambda b: b.manifest["entries"].remove(b.entry("core-quality")))

    def test_empty_required_list(self):
        self.assert_fails(lambda b: b.manifest["execution_policy"].update(required_protocols=[]))

    def test_non_core_in_required_list(self):
        self.assert_fails(lambda b: b.manifest["execution_policy"].update(
            required_protocols=["core-governance", "core-quality", "core-output", "visual-editorial"]))

    def test_missing_default(self):
        self.assert_fails(lambda b: b.manifest["execution_policy"].update(default_presentation="present-gone"))

    def test_disallowed_status(self):
        self.assert_fails(lambda b: b.entry("present-pitch").update(status="deprecated"), presentation="present-pitch")

    def test_path_traversal(self):
        self.assert_fails(lambda b: b.entry("core-output").update(path="../secret.json"))

    def test_cli_exit_code_is_2(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "resolve.py"), "--topic", "x", "--goal", "y",
                                 "--audience", "z", "--local", str(ROOT), "--presentation", "nope"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("PROTOCOL RESOLUTION FAILED", result.stderr)


if __name__ == "__main__":
    unittest.main()
