#!/usr/bin/env python3
"""Resolve one version-pinned, hash-verified Creativity presentation context. Stdlib only."""
import argparse, hashlib, json, re, sys, urllib.request
from pathlib import Path

REPO = "obuchenie-testove/creativity-ai-studio"
PREFIX = "presentation-protocol-engine/protocol-bank"
HEAD_API = f"https://api.github.com/repos/{REPO}/commits/main"
SHA_LEN = 40

class ProtocolError(RuntimeError):pass

def get_url(url):
    req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json", "User-Agent":"Creativity-Presentation-Resolver/0.1"})
    with urllib.request.urlopen(req, timeout=20) as response:return response.read()

def snapshot(local=None, ref=None, fetch=get_url):
    if local:
        root=Path(local)
        return "LOCAL-TEST-SNAPSHOT", lambda path:(root/path).read_bytes()
    if ref is None:
        head=json.loads(fetch(HEAD_API))
        ref=head.get("sha")
    if not ref or len(ref)!=SHA_LEN or any(c not in '0123456789abcdef' for c in ref.lower()):
        raise ProtocolError('Cannot resolve a valid immutable Git commit SHA')
    return ref, lambda path:fetch(f"https://raw.githubusercontent.com/{REPO}/{ref}/{PREFIX}/{path}")

def read_json(data):
    return json.loads(data.decode('utf-8'))

def pick(entries, kind, text, explicit, default):
    choices=[e for e in entries if e['kind']==kind]
    if explicit:
        match=[e for e in choices if e['id']==explicit]
        if not match:raise ProtocolError('Unknown '+kind+' protocol ID: '+explicit)
        return match[0]
    words=text.lower()
    scored=[]
    for e in choices:
        score=sum(1 for t in e.get('tags',[]) if (re.search(r'(?<![a-z])'+re.escape(t.lower())+r'(?![a-z])', words) if t.isascii() else t.lower() in words))
        if score:scored.append((score,e.get('priority',0),e['id'],e))
    return sorted(scored,key=lambda a:(-a[0],-a[1],a[2]))[0][3] if scored else next(e for e in choices if e['id']==default)

def resolve(args, fetch=get_url):
    sha,load=snapshot(args.local,args.ref,fetch)
    manifest=read_json(load('manifest.json'))
    if manifest.get('manifest_schema')!='creativity.presentation-manifest/1.0':raise ProtocolError('Unsupported manifest schema')
    entries=manifest['entries'];index={e['id']:e for e in entries}
    if len(index)!=len(entries):raise ProtocolError('Duplicate protocol IDs')
    input_text=' '.join([args.topic,args.goal,args.audience,args.intent or '',args.visual_hint or ''])
    required=manifest['execution_policy']['required_protocols']
    wanted=list(required)
    wanted.append(pick(entries,'presentation',input_text,args.presentation,manifest['execution_policy']['default_presentation'])['id'])
    wanted.append(pick(entries,'visual',input_text,args.visual,manifest['execution_policy']['default_visual'])['id'])
    if args.thinking:wanted.append(pick(entries,'thinking',input_text,args.thinking,None)['id'])
    loaded=[]
    for pid in wanted:
        entry=index[pid]
        raw=load(entry['path']);digest=hashlib.sha256(raw).hexdigest()
        if digest != entry['sha256']:raise ProtocolError('SHA256 mismatch for '+pid)
        item=read_json(raw)
        if item.get('id')!=pid or item.get('version')!=entry['version'] or item.get('kind')!=entry['kind'] or item.get('protocol_schema')!='creativity.presentation-protocol/1.0':
            raise ProtocolError('Protocol metadata mismatch for '+pid)
        loaded.append({'id':pid,'version':entry['version'],'sha256':digest,'kind':entry['kind'],'status':entry['status'],'content':item})
    return {'status':'pilot-needs-expert-review','source_repository':REPO,'git_commit':sha,
      'brief':{'topic':args.topic,'goal':args.goal,'audience':args.audience,'minutes':args.minutes,'slides':args.slides,'format':args.format,'language':args.language},
      'selected_protocols':loaded,'validation':{'manifest':'ok','hashes':'ok','conflicts':'needs-review-by-agent','rendered_file':'not-created-by-resolver'},
      'next_step':'Use selected protocols in host AI to produce slide outline and (if available) file; then evaluate and report.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--topic',required=True);p.add_argument('--goal',required=True);p.add_argument('--audience',required=True)
    p.add_argument('--minutes',type=int,default=15);p.add_argument('--slides',type=int,default=None)
    p.add_argument('--language',default='bg');p.add_argument('--format',default='outline')
    p.add_argument('--intent',default='');p.add_argument('--visual-hint',default='')
    p.add_argument('--presentation');p.add_argument('--visual');p.add_argument('--thinking')
    p.add_argument('--local',help='Local protocol-bank directory for tests/offline snapshot')
    p.add_argument('--ref',help='Fixed Git commit SHA; omit to resolve current main')
    p.add_argument('--output',default='-')
    a=p.parse_args()
    try: result=resolve(a)
    except (ProtocolError,OSError,ValueError,KeyError) as exc:
        print('PROTOCOL RESOLUTION FAILED: '+str(exc),file=sys.stderr);sys.exit(2)
    value=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.output=='-':print(value,end='')
    else:Path(a.output).write_text(value,encoding='utf-8')
if __name__=='__main__':main()
