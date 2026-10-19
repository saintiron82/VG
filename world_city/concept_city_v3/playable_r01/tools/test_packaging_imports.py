#!/usr/bin/env python3
"""Verify the exact import-only closure in an isolated temporary repository.

No scene generation, voxel compilation, or sealed pack writes occur. The test
copies only packaging_dependencies.json's explicit files, preserves their bytes,
then imports the two real entrypoints with Python's isolated (-I) mode. An audit
hook rejects original-repository fallback reads and any repository write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'voxel_character').is_dir())

CHILD = r'''
import importlib.util,json,os,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(sys.argv[1]).resolve();original=Path(sys.argv[2]).resolve()
entrypoints=json.loads(sys.argv[3]);opened=set();write_flags=os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND
def audit(event,args):
    if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
    p=Path(os.fsdecode(args[0]));p=(p if p.is_absolute() else Path.cwd()/p).resolve()
    if p.is_relative_to(original):raise RuntimeError('Forbidden original-repository fallback: '+str(p))
    if p.is_relative_to(root):
        if isinstance(args[2],int) and args[2]&write_flags:raise RuntimeError('Unexpected repository write during import: '+str(p))
        if p.is_file():opened.add(str(p.relative_to(root)))
sys.addaudithook(audit);sys.path.insert(0,str(root))
loaded=[]
for i,relative in enumerate(entrypoints):
    path=root/relative;spec=importlib.util.spec_from_file_location('packaging_import_'+str(i),path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    loaded.append({'entrypoint':relative,'path_resolved_inside_isolated_root':Path(module.__file__).resolve().is_relative_to(root)})
external=set()
for name,module in list(sys.modules.items()):
    path=getattr(module,'__file__','') or ''
    if 'site-packages' in path:external.add(name.split('.')[0])
print(json.dumps({'status':'PASS','entrypoints':loaded,'observed_files':sorted(opened),'external_import_roots':sorted(external),'original_repository_fallback_reads':0,'repository_writes':0},sort_keys=True))
'''


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT,
                        help='Repository supplying the explicit dependency files')
    parser.add_argument('--dependencies', type=Path,
                        default=HERE/'packaging_dependencies.json')
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = json.loads(args.dependencies.read_bytes())
    rows = manifest['dependencies']
    expected = {row['path'] for row in rows}
    if len(expected) != len(rows):
        raise ValueError('Duplicate dependency path')
    with tempfile.TemporaryDirectory(prefix='riverstone-import-closure-') as temporary:
        isolated = Path(temporary)/'repo'
        isolated.mkdir()
        for row in rows:
            source = (root/row['path']).resolve()
            if not source.is_relative_to(root):
                raise ValueError('Dependency escapes repository')
            if source.stat().st_size != row['bytes'] or sha(source) != row['sha256']:
                raise ValueError('Dependency source changed: ' + row['path'])
            target = isolated/row['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        # The repository root resolver uses this common framework directory.
        (isolated/'voxel_character').mkdir(exist_ok=True)
        result = subprocess.run([sys.executable, '-I', '-B', '-c', CHILD,
                                 str(isolated), str(root), json.dumps(manifest['import_entrypoints'])],
                                cwd=isolated, text=True, capture_output=True, timeout=120)
        if result.returncode:
            raise RuntimeError('Isolated import failed:\n' + result.stdout + result.stderr)
        report = json.loads(result.stdout.strip().splitlines()[-1])
        unlisted = set(report['observed_files']) - expected
        if unlisted:
            raise ValueError('Unlisted dependency reads: ' + repr(sorted(unlisted)))
        for row in rows:
            if sha(isolated/row['path']) != row['sha256']:
                raise ValueError('Import changed copied source: ' + row['path'])
        report.update(dependency_files=len(rows), dependency_bytes=sum(r['bytes'] for r in rows),
                      all_copied_file_hashes_preserved=True,
                      scope='Import closure only; source geometry/hash/deep runtime verification remain separate')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
