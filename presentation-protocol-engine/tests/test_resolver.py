import argparse, copy, hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import resolve

ROOT=Path(__file__).resolve().parents[1]/'protocol-bank'

def arguments(**kwargs):
    a=dict(topic='How our AI teams work',goal='Get decision on a new operating model',audience='leadership',minutes=15,slides=10,language='bg',format='outline',intent='',visual_hint='',presentation=None,visual=None,thinking=None,local=str(ROOT),ref=None)
    a.update(kwargs);return argparse.Namespace(**a)

class ResolverTest(unittest.TestCase):
    def test_manifest_hashes_and_unique_ids(self):
        m=json.loads((ROOT/'manifest.json').read_text())
        ids=[e['id'] for e in m['entries']]
        self.assertEqual(len(ids),len(set(ids)))
        for e in m['entries']:
            blob=(ROOT/e['path']).read_bytes()
            self.assertEqual(hashlib.sha256(blob).hexdigest(),e['sha256'])

    def test_explicit_selection(self):
        run=resolve.resolve(arguments(presentation='present-storytelling',visual='visual-editorial',thinking='think-systems'))
        self.assertEqual([p['id'] for p in run['selected_protocols']][-3:],['present-storytelling','visual-editorial','think-systems'])
        self.assertEqual(run['git_commit'],'LOCAL-TEST-SNAPSHOT')

    def test_auto_selection(self):
        run=resolve.resolve(arguments(topic='Investor pitch for startup',intent='pitch'))
        self.assertEqual(run['selected_protocols'][3]['id'],'present-pitch')

    def test_change_requires_manifest_hash_update(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'presentation').mkdir();
            m=json.loads((ROOT/'manifest.json').read_text())
            for e in m['entries']:
                src=ROOT/e['path'];dest=root/e['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(src.read_bytes())
            (root/'manifest.json').write_text(json.dumps(m))
            target=root/'presentation/present-pitch.json'
            obj=json.loads(target.read_text());obj['rules'].append('New live external rule')
            target.write_text(json.dumps(obj),encoding='utf-8')
            with self.assertRaises(resolve.ProtocolError):resolve.resolve(arguments(local=str(root),presentation='present-pitch'))
            entry=next(e for e in m['entries'] if e['id']=='present-pitch')
            entry['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
            entry['version']='0.1.1';obj['version']='0.1.1';target.write_text(json.dumps(obj),encoding='utf-8')
            entry['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
            (root/'manifest.json').write_text(json.dumps(m))
            run=resolve.resolve(arguments(local=str(root),presentation='present-pitch'))
            self.assertEqual(run['selected_protocols'][3]['version'],'0.1.1')
            self.assertIn('New live external rule',run['selected_protocols'][3]['content']['rules'])

    def test_unknown_protocol_fails_closed(self):
        with self.assertRaises(resolve.ProtocolError):resolve.resolve(arguments(presentation='present-fictitious'))

if __name__=='__main__':unittest.main()
