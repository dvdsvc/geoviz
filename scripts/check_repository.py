"""Check the publication candidate without network access or model calls."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import tomllib
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def candidate_files():
    if (ROOT/'.git').is_dir():
        data=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT)
        return sorted({ROOT/name.decode() for name in data.split(b'\0') if name})
    excluded={'.git','.venv','node_modules','.next','__pycache__','runs','build','dist'}
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and
                  not set(p.relative_to(ROOT).parts)&excluded and
                  not p.name.endswith(('.pyc','.tsbuildinfo')) and
                  p.name!='next-env.d.ts')


def main():
    failures=[];links=0
    candidates=candidate_files();names={p.relative_to(ROOT).as_posix() for p in candidates}
    manifest=json.loads((ROOT/'provenance/source_manifest.json').read_text())
    for entry in manifest['files']:
        path=ROOT/entry['path']
        if entry['path'] not in names:
            failures.append(f"Copied source omitted from candidate: {entry['path']}")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            failures.append(f"Copied source hash mismatch: {entry['path']}")
        if not entry['changes'] and entry['sha256']!=entry['source_sha256']:
            failures.append(f"Unexplained source change: {entry['path']}")
    patterns={
        'API credential':re.compile(r'\b(?:sk-|AIza|ghp_|github_pat_)[A-Za-z0-9_-]{20,}\b'),
        'AWS access ID':re.compile(r'\bAKIA[A-Z0-9]{16}\b'),
        'private key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        'SSH password command':re.compile(r'sshpass\s+-p\s+'),
        'personal home path':re.compile('/'+'Users'+r'/[^\s"<>]+|'+'/'+'home'+r'/[^\s"<>]+'),
    }
    binaries=[]
    for path in candidates:
        relative=path.relative_to(ROOT).as_posix()
        if path.is_symlink():failures.append(f'Unexpected symlink: {relative}');continue
        if path.stat().st_size>=50*1024*1024:failures.append(f'File exceeds 50 MiB: {relative}')
        if path.suffix.lower() in {'.pdf','.xlsx','.xls','.sqlite','.sqlite3','.db','.pem','.key','.zip'} or path.name=='.env':
            failures.append(f'Private/bulky input candidate: {relative}')
        if path.suffix.lower() in {'.png','.jpg'} and relative.startswith('assets/screenshots/'):
            signature=b'\x89PNG\r\n\x1a\n' if path.suffix.lower()=='.png' else b'\xff\xd8'
            if not path.read_bytes().startswith(signature):failures.append(f'Invalid screenshot format: {relative}')
            binaries.append(relative);continue
        if relative=='frontend/src/app/favicon.ico':
            binaries.append(relative);continue
        try:text=path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            failures.append(f'Unexpected binary: {relative}');continue
        for label,pattern in patterns.items():
            if pattern.search(text):failures.append(f'Potential {label}: {relative} (value suppressed)')
        if path.suffix=='.py':compile(text,relative,'exec')
        if path.suffix=='.json':json.loads(text)
        if path.suffix=='.toml' or path.name=='uv.lock':tomllib.loads(text)
        if path.suffix=='.svg':ET.fromstring(text)
        if path.suffix=='.md':
            if len(re.findall(r'^```',text,re.M))%2:failures.append(f'Unbalanced code fence: {relative}')
            targets=re.findall(r'\]\(([^)]+)\)',text)+re.findall(r'<img[^>]+src="([^"]+)"',text)
            for target in targets:
                target=target.split(' "',1)[0];parsed=urlsplit(target)
                if parsed.scheme or target.startswith('#'):continue
                destination=(path.parent/unquote(parsed.path)).resolve();links+=1
                if not destination.is_relative_to(ROOT) or not destination.exists():
                    failures.append(f'Broken/escaping local link: {relative} -> {target}')
    headings=[re.findall(r'^## (.+)$',(ROOT/name).read_text(),re.M) for name in ('README.md','README.zh-CN.md')]
    if len(headings[0])!=8 or len(headings[1])!=8:failures.append('Bilingual README section mismatch')
    for required in ('frontend/.env.example','.env.example','.github/workflows/check.yml'):
        if required not in names:failures.append(f'Required candidate missing: {required}')
    samples=json.loads((ROOT/'frontend/src/data/realSamples.json').read_text())
    spots=json.loads((ROOT/'frontend/src/data/realSpots.json').read_text())
    if len(samples)!=8 or len(spots)!=48 or not all(s['sampleId'].startswith('DEMO') for s in samples):
        failures.append('Unexpected data in synthetic publication fixture')
    if {s['sample_id'] for s in spots}!={s['sampleId'] for s in samples}:
        failures.append('Synthetic sample/spot identity mismatch')
    workflow=(ROOT/'.github/workflows/check.yml').read_text()
    for command in ('run build','run typecheck','scripts/check_backend.py','scripts/check_science.mjs','scripts/check_repository.py'):
        if command not in workflow:failures.append(f'Workflow command missing: {command}')
    if 'continue-on-error: true' not in workflow:failures.append('Retained lint findings must be explicit in CI')
    result={'source_manifest_files_checked':len(manifest['files']),
        'byte_identical_source_copies':sum(not e['changes'] for e in manifest['files']),
        'candidate_files':len(candidates),'candidate_total_bytes':sum(p.stat().st_size for p in candidates),
        'largest_candidate_bytes':max(p.stat().st_size for p in candidates),
        'local_document_links_checked':links,'allowed_binary_files':binaries,
        'failures':failures,'scan_scope':'heuristic token/path patterns and candidate review; not an exhaustive security audit'}
    print(json.dumps(result,indent=2))
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
