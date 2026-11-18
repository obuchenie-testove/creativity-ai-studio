#!/usr/bin/env python3
"""Read a pinned protocol bank; never execute downloaded code or query institutional records."""
import argparse
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

REPOSITORY = 'obuchenie-testove/creativity-ai-studio'
PREFIXES = {'kindergarten-administration-engine', 'kindergarten-situation-engine'}
KINDS = {'core', 'role', 'task', 'source'}
USABLE = {'pilot', 'approved', 'active'}

class ProtocolError(ValueError):
    pass

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def fetch_url(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Creativity-KG/0.1', 'Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ProtocolError('Source exceeds size limit')
    return raw

def json_read(raw):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ProtocolError('Duplicate JSON property: '+key)
            result[key] = value
        return result
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_pairs)

def safe_path(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ProtocolError('Invalid protocol path')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or str(path) != value or not value.endswith('.json'):
        raise ProtocolError('Unsafe protocol path: '+value)
    return value

def load_snapshot(root, live=False, ref=None, fetch=fetch_url):
    root = Path(root).resolve()
    config = json_read((root/'references/deployment.json').read_bytes())
    if config.get('repository') != REPOSITORY or config.get('prefix') not in PREFIXES:
        raise ProtocolError('Untrusted repository configuration')
    if ref and not live:
        raise ProtocolError('--ref requires --live')
    if live:
        if ref is None:
            branch = urllib.parse.quote(config['branch'], safe='')
            ref = json_read(fetch(f'https://api.github.com/repos/{REPOSITORY}/commits/{branch}')).get('sha')
        if not isinstance(ref, str) or not re.fullmatch('[0-9a-f]{40}', ref):
            raise ProtocolError('Cannot pin a full immutable commit SHA')
        prefix = f"https://raw.githubusercontent.com/{REPOSITORY}/{ref}/{config['prefix']}/references/protocol-bank/"
        read = lambda path: fetch(prefix+safe_path(path))
    else:
        bank = (root/'references/protocol-bank').resolve()
        def read(path):
            target = (bank/safe_path(path)).resolve()
            if not target.is_relative_to(bank):
                raise ProtocolError('Protocol escapes local bank')
            return target.read_bytes()
    return config, ref if live else config.get('seed_commit'), read

def resolve(root, task, roles=None, sources=None, live=False, ref=None, fetch=fetch_url):
    config, commit, read = load_snapshot(root, live, ref, fetch)
    manifest_raw = read('manifest.json')
    manifest = json_read(manifest_raw)
    if manifest.get('manifest_schema') != 'creativity.kg-manifest/1.0' or manifest.get('engine') != config['prefix']:
        raise ProtocolError('Manifest schema or engine mismatch')
    if manifest.get('status') not in USABLE:
        raise ProtocolError('Manifest is not usable')
    entries = manifest.get('entries')
    if not isinstance(entries, list) or not entries:
        raise ProtocolError('Missing entries')
    index = {}
    paths = set()
    for entry in entries:
        pid = entry.get('id')
        if not isinstance(pid,str) or not re.fullmatch('[a-z][a-z0-9-]*',pid) or pid in index:
            raise ProtocolError('Invalid or duplicate protocol ID')
        kind = entry.get('kind')
        path = safe_path(entry.get('path'))
        if kind not in KINDS or path in paths or not path.startswith(kind+'/'):
            raise ProtocolError('Invalid kind or duplicate path')
        if not isinstance(entry.get('sha256'),str) or not re.fullmatch('[0-9a-f]{64}',entry['sha256']):
            raise ProtocolError('Invalid SHA256')
        if not isinstance(entry.get('version'),str) or not entry['version']:
            raise ProtocolError('Missing protocol version')
        index[pid]=entry;paths.add(path)
    def check_ids(ids,kind):
        if len(ids) != len(set(ids)):
            raise ProtocolError('Duplicate selection')
        if any(pid not in index or index[pid]['kind'] != kind for pid in ids):
            raise ProtocolError('Unknown or wrong-kind '+kind+' selection')
    cores=manifest.get('required_core',[])
    check_ids(cores,'core')
    if set(cores) != {e['id'] for e in entries if e['kind']=='core'}:
        raise ProtocolError('Every core must be required')
    selected_roles=list(manifest.get('task_roles', {}).get(task, manifest['default_roles']) if roles is None else roles)
    check_ids(selected_roles,'role')
    limits=manifest['selection_limits']
    if not limits['role_min'] <= len(selected_roles) <= min(limits['role_max'],5):
        raise ProtocolError('Role count outside limits')
    completer=manifest['completer_role']
    if completer not in selected_roles:
        raise ProtocolError('Completer role is required')
    selected_roles=[r for r in selected_roles if r!=completer]+[completer]
    check_ids([task],'task')
    selected_sources=['source-official','source-internal'] if sources is None else list(sources)
    check_ids(selected_sources,'source')
    if len(selected_sources)>min(limits['source_max'],2):
        raise ProtocolError('Too many source protocols')
    loaded=[]
    for pid in cores+selected_roles+[task]+selected_sources:
        entry=index[pid]
        if entry.get('status') not in USABLE:
            raise ProtocolError('Unusable protocol: '+pid)
        raw=read(entry['path'])
        if digest(raw)!=entry['sha256']:
            raise ProtocolError('SHA256 mismatch: '+pid)
        item=json_read(raw)
        if item.get('protocol_schema') != 'creativity.kg-protocol/1.0' or item.get('engine')!=manifest['engine']:
            raise ProtocolError('Protocol schema or engine mismatch: '+pid)
        if any(item.get(k)!=entry[k] for k in ['id','version','kind','status']):
            raise ProtocolError('Protocol metadata mismatch: '+pid)
        if not isinstance(item.get('rules'),list) or not item['rules'] or any(not isinstance(r,str) or not r.strip() for r in item['rules']):
            raise ProtocolError('Missing protocol rules: '+pid)
        loaded.append({'id':pid,'version':entry['version'],'kind':entry['kind'],'sha256':entry['sha256'],'content':item})
    return {'schema':'creativity.kg-context/1.0','engine':manifest['engine'],'version':manifest['version'],
            'status':'pilot-for-human-review','mode':'live-pinned' if live else 'bundled-snapshot',
            'source_repository':REPOSITORY,'source_commit':commit,'snapshot_sha256':digest(manifest_raw),
            'integrity_status':'PASS','source_status':'NOT_QUERIED','task_id':task,'role_order':selected_roles,
            'selected_protocols':loaded,'next_action':'Execute the selected task under core rules; fetch applicable evidence using permitted host tools.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--task',required=True)
    parser.add_argument('--roles',nargs='+')
    parser.add_argument('--sources',nargs='*')
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--ref')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        result=resolve(args.root,args.task,args.roles,args.sources,args.live,args.ref)
        value=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if args.output:
            args.output.write_text(value,encoding='utf-8')
        else:
            print(value,end='')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('PROTOCOL LOAD BLOCKED: '+str(exc),file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':
    sys.exit(main())
