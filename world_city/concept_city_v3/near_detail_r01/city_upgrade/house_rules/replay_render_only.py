"""Restore a render-only compiler snapshot into an isolated tree and replay it.

All selected input and code hashes are checked before copying. This helper never
changes current compiler code or source masters. The isolated tree and output
remain available as replay evidence; use a new --workspace for every run.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import layered_qa as qa


def replay(stats_path,workspace):
    stats=json.loads(Path(stats_path).read_text());contract=stats['replay_contract']
    workspace=Path(workspace).resolve()
    if workspace.exists():raise ValueError('Replay workspace must be new')
    workspace.mkdir(parents=True)
    restored=[]
    for kind,records in [('code',contract['code_snapshots']),('input',contract['inputs'])]:
        for role,r in records.items():
            source=qa.ROOT/r.get('snapshot_path',r.get('path',''))
            target=workspace/r.get('original_path',r.get('path',''))
            if not target.is_relative_to(workspace):raise ValueError('Replay path leaves isolated tree')
            if qa._file_info(source)['sha256']!=r['sha256']:raise ValueError('Replay input/snapshot hash mismatch: '+role)
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and qa._file_info(target)['sha256']!=r['sha256']:raise ValueError('Conflicting replay paths')
            if not target.exists():shutil.copyfile(source,target)
            restored.append({'role':role,'kind':kind,'path':str(target.relative_to(workspace)),'sha256':r['sha256']})
    command=[sys.executable if i==0 else str(workspace/'replayed_output') if v=='<NEW_EMPTY_OUTPUT_DIRECTORY>' else v for i,v in enumerate(contract['command'])]
    limits=contract.get('checkpoint_resume',{})
    if limits and (limits.get('max_sessions')!=2 or limits.get('per_session_wall_seconds')!=900):raise ValueError('Unapproved replay execution limit')
    for attempt in range(1,limits.get('max_sessions',1)+1):
        args=command+(['--resume-checkpoint'] if attempt>1 else [])
        process=subprocess.run(args,cwd=workspace,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=900)
        log=workspace/('replay.log' if attempt==1 else 'replay.resume_2.log');log.write_text(process.stdout)
        if process.returncode==0:break
        if process.returncode!=limits.get('soft_exit_code') or attempt==limits.get('max_sessions',1):
            raise ValueError('Isolated replay failed; inspect '+str(log))
    replayed=json.loads((workspace/'replayed_output'/(stats['asset_key']+'.layered.stats.json')).read_text())
    checks={k:replayed.get(k)==stats.get(k) for k in ('source_master_sha256','authored_master_sha256','full_fine_fingerprint','fine_face_fingerprint','occupancy_certificate_sha256','reference_full_fine_cells','quads','visible_unit_faces')}
    checks['render_bytes_same']=replayed['files']['.render.json']['sha256']==stats['files']['.render.json']['sha256']
    report={'schema':'riverstone.house_detail.isolated_replay.v1','pass':all(checks.values()),'checks':checks,'restored':restored,
            'input_stats':qa._file_info(stats_path),'replay_stats_path':str(workspace/'replayed_output'/(stats['asset_key']+'.layered.stats.json')),
            'max_rss_kib':replayed['max_rss_kib'],'elapsed_seconds':replayed['elapsed_seconds']}
    (workspace/'validation.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stats',required=True,type=Path);p.add_argument('--workspace',required=True,type=Path);x=p.parse_args()
    result=replay(x.stats,x.workspace);print(json.dumps(result));raise SystemExit(0 if result['pass'] else 1)
