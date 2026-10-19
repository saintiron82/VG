#!/usr/bin/env python3
"""Audit provenance and completeness independently of route success.
A verified report may honestly contain blocked/unsupported routes.
"""
import argparse,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(prepared_path,report_path):
 p=json.loads(Path(prepared_path).read_text());r=json.loads(Path(report_path).read_text());errors=[]
 if r.get('status') not in ('pass','fail'):errors.append('Physics suite did not finish')
 if r.get('prepared_sha256')!=digest(prepared_path):errors.append('Prepared suite changed after execution')
 for name,source in p['sources'].items():
  if not Path(source['path']).exists() or digest(source['path'])!=source['sha256']:errors.append('Manifest changed: '+name)
  if r.get('source_hashes',{}).get(name)!=source:errors.append('Report manifest binding differs: '+name)
 for relative,sha in p['implementation_hashes'].items():
  if digest(Path(p['repo_root'])/relative)!=sha:errors.append('Harness changed after execution: '+relative)
 for key,asset in p['assets'].items():
  if digest(Path(p['repo_root'])/asset['render_path'])!=asset['render_sha256']:errors.append('Render changed: '+key)
 expected={v['id']:v for v in p['routes']};actual={v['id']:v for v in r.get('routes',[])}
 if set(expected)!=set(actual):errors.append('Prepared/report route IDs differ')
 if len(actual)!=len(r.get('routes',[])):errors.append('Duplicate route IDs')
 outcomes=[]
 for id,result in actual.items():
  fixture=expected.get(id,{})
  if result.get('within_route_teleports')!=0:errors.append('Teleport policy violation: '+id)
  if result.get('status')=='reached':
   if result['waypoints_reached']!=result['waypoints_total']:errors.append('Incomplete reached trace: '+id)
   if len(result.get('waypoint_reached_frames',[]))!=result['waypoints_total']-1:errors.append('Missing waypoint evidence: '+id)
  if result.get('pass') and 'expected_failure' not in fixture:
   if result.get('status')!='reached' or result.get('not_on_floor_frames') or result.get('ground_ray_miss_frames') or result.get('non_fine_support_frames'):errors.append('False route pass: '+id)
  if 'expected_failure' in fixture and result.get('pass'):
   if result.get('status')!=fixture['expected_failure']:errors.append('False negative-control pass: '+id)
   if fixture.get('expected_contact_id') and fixture['expected_contact_id'] not in result.get('obstacle_contact_ids',{}):errors.append('Negative control lacks expected collider: '+id)
  outcomes.append({'id':id,'kind':result['kind'],'pass':result['pass'],'status':result['status'],
    'not_on_floor_frames':result['not_on_floor_frames'],'ground_ray_miss_frames':result['ground_ray_miss_frames'],
    'non_fine_support_frames':result.get('non_fine_support_frames'),
    'contact_ids':list(result.get('obstacle_contact_ids',{}))})
 return {'evidence_integrity':'verified' if not errors else 'invalid','errors':errors,
   'physics_status':r.get('status'),'all_routes_passed':all(v['pass'] for v in outcomes),
   'scope':'fixed actual-geometry sampled routes; generic capsule, not whole-city/production controller/NPC certification',
   'sources':p['sources'],'summary':r.get('summary',{}),'outcomes':outcomes}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--prepared',required=True);ap.add_argument('--report',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
 out=audit(a.prepared,a.report);Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));raise SystemExit(0 if out['evidence_integrity']=='verified' else 2)
