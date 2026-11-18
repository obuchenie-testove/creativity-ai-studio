"""Boundary tests using synthetic data only; no institutional system is queried."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('resolver',Path(__file__).with_name('resolve.py'))
resolver=importlib.util.module_from_spec(spec);spec.loader.exec_module(resolver)
ROOT=Path(__file__).resolve().parents[1]

class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/'skill';shutil.copytree(ROOT,self.root)
        self.bank=self.root/'references/protocol-bank'
        self.manifest=json.loads((self.bank/'manifest.json').read_text())
        self.task=next(e['id'] for e in self.manifest['entries'] if e['kind']=='task')
    def tearDown(self):self.temp.cleanup()
    def save_manifest(self):
        (self.bank/'manifest.json').write_text(json.dumps(self.manifest))
    def test_every_task_and_pack(self):
        for e in self.manifest['entries']:
            if e['kind']!='task':continue
            result=resolver.resolve(self.root,e['id'])
            self.assertEqual(result['integrity_status'],'PASS')
            self.assertEqual(result['source_status'],'NOT_QUERIED')
            self.assertEqual(result['role_order'][-1],'role-completer')
            self.assertEqual(sum(p['kind']=='task' for p in result['selected_protocols']),1)
            self.assertTrue((self.root/'references/packs'/f"{e['id'][5:]}.md").is_file())
    def test_tampered_protocol(self):
        p=self.bank/self.manifest['entries'][0]['path'];p.write_text(p.read_text()+' ')
        with self.assertRaisesRegex(resolver.ProtocolError,'SHA256'):resolver.resolve(self.root,self.task)
    def test_duplicate_id(self):
        self.manifest['entries'].append(self.manifest['entries'][0]);self.save_manifest()
        with self.assertRaises(resolver.ProtocolError):resolver.resolve(self.root,self.task)
    def test_path_traversal(self):
        self.manifest['entries'][0]['path']='../outside.json';self.save_manifest()
        with self.assertRaises(resolver.ProtocolError):resolver.resolve(self.root,self.task)
    def test_missing_core(self):
        self.manifest['required_core']=[];self.save_manifest()
        with self.assertRaises(resolver.ProtocolError):resolver.resolve(self.root,self.task)
    def test_missing_file(self):
        (self.bank/self.manifest['entries'][0]['path']).unlink()
        with self.assertRaises(OSError):resolver.resolve(self.root,self.task)
    def test_wrong_task(self):
        with self.assertRaises(resolver.ProtocolError):resolver.resolve(self.root,'role-completer')
    def test_duplicate_role(self):
        with self.assertRaises(resolver.ProtocolError):resolver.resolve(self.root,self.task,['role-completer','role-completer'])
    def test_missing_completer(self):
        with self.assertRaises(resolver.ProtocolError):resolver.resolve(self.root,self.task,['role-source-checker'])
    def test_source_limits(self):
        with self.assertRaises(resolver.ProtocolError):resolver.resolve(self.root,self.task,sources=['source-official']*3)
    def test_deprecated(self):
        self.manifest['entries'][0]['status']='deprecated';self.save_manifest()
        with self.assertRaises(resolver.ProtocolError):resolver.resolve(self.root,self.task)
    def test_metadata_tamper(self):
        e=self.manifest['entries'][0];p=self.bank/e['path'];item=json.loads(p.read_text());item['engine']='other';p.write_text(json.dumps(item));e['sha256']=resolver.digest(p.read_bytes());self.save_manifest()
        with self.assertRaisesRegex(resolver.ProtocolError,'engine'):resolver.resolve(self.root,self.task)
    def test_all_live_files_pinned(self):
        urls=[];sha='a'*40
        prefix=f"https://raw.githubusercontent.com/{resolver.REPOSITORY}/{sha}/{self.manifest['engine']}/references/protocol-bank/"
        def fetch(url):
            urls.append(url)
            if '/commits/' in url:return json.dumps({'sha':sha}).encode()
            self.assertTrue(url.startswith(prefix));return (self.bank/url.removeprefix(prefix)).read_bytes()
        result=resolver.resolve(self.root,self.task,live=True,fetch=fetch)
        self.assertEqual(result['source_commit'],sha)
        self.assertEqual(sum('/commits/' in x for x in urls),1)
    def test_invalid_ref(self):
        with self.assertRaises(resolver.ProtocolError):resolver.resolve(self.root,self.task,live=True,ref='main')
    def test_no_hidden_network_in_snapshot(self):
        def fail(url):self.fail('Unexpected network access')
        self.assertEqual(resolver.resolve(self.root,self.task,fetch=fail)['mode'],'bundled-snapshot')

if __name__=='__main__':unittest.main()
