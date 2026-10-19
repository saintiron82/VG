#!/usr/bin/env python3
"""Reject partial, stale, or structurally inconsistent whole-city evidence."""
import argparse, hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(prepared_path,report_path):
 p=json.loads(Path(prepared_path).read_text());r=json.loads(Path(report_path).read_text());errors=[]
 if r.get('status')!='pass':errors.append('Physics suite did not pass')
 if r.get('prepared_sha256')!=digest(prepared_path):errors.append('Prepared suite changed after execution')
 for which in ('scene','infrastructure'):
  path=p['sources'][which+'_path'];sha=p['sources'][which+'_sha256']
  if digest(path)!=sha:errors.append(which+' manifest changed after preparation')
  if r.get('source_hashes',{}).get(which+'_sha256')!=sha:errors.append(which+' report hash differs')
 for key,a in p['assets'].items():
  if digest(Path(p['repo_root'])/a['render_path'])!=a['render_sha256']:errors.append('Render asset changed: '+key)
 positive=[x for x in r.get('routes',[]) if 'expected_failure' not in x]
 if {x['id'] for x in positive}!={x['id'] for x in p['routes']}:errors.append('Not all prepared positive routes ran')
 if len(positive)!=len({x['id'] for x in positive}):errors.append('Duplicate route IDs')
 for x in positive:
  if not x.get('pass') or x['status']!='reached':errors.append('Route failed: '+x['id'])
  if x['waypoints_reached']!=x['waypoints_total']:errors.append('Missed waypoint: '+x['id'])
  if x['physics_frames']<=0 or x.get('within_route_teleports')!=0:errors.append('Invalid movement evidence: '+x['id'])
  if x['not_on_floor_frames'] or x['ground_ray_miss_frames']:errors.append('Ground loss: '+x['id'])
  if len(x.get('waypoint_reached_frames',[]))!=x['waypoints_total']-1:errors.append('Incomplete waypoint trace: '+x['id'])
 expected={rid for route in p['routes'] for rid in route['source_road_ids']}
 actual={rid for route in positive for rid in route['source_road_ids']}
 if expected!=actual:errors.append('Ground segment coverage differs')
 if len(expected)!=p['coverage']['source_ground_segments']:errors.append('Prepared suite omits source ground segments')
 negatives={x['id']:x for x in r.get('routes',[]) if 'expected_failure' in x}
 for id in ('NEGATIVE_RIVER_HAS_NO_INFINITE_FLOOR','NEGATIVE_CASTLE_WALL_IS_SOLID'):
  if id not in negatives or not negatives[id]['pass']:errors.append('Missing or failed control: '+id)
 castle=negatives.get('NEGATIVE_CASTLE_WALL_IS_SOLID',{})
 if not castle.get('obstacle_contact_ids',{}).get('D01-B001',0):errors.append('Wall control did not report castle collider')
 out={'status':'pass' if not errors else 'fail','errors':errors,'warnings':[{'route_id':x['id'],'obstacle_contacts':x['obstacle_contact_ids'],'max_centerline_error_m':x['max_centerline_error_m']} for x in positive if x['obstacle_contact_ids']],'source_hashes':p['sources'],
      'positive_routes':len(positive),'source_ground_segments_covered':len(actual),'negative_controls':len(negatives),
      'scope':'generic capsule, flat-grade exterior only; not production controller, navigation, NPCs, interiors, or elevated wall walks',
      'physics_summary':r.get('summary')}
 return out
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--prepared',default=str(HERE/'prepared.json'));parser.add_argument('--report',default=str(HERE/'evidence/traversal_results.json'));parser.add_argument('--output',default=str(HERE/'evidence/report_audit.json'));a=parser.parse_args()
 result=audit(a.prepared,a.report);Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='pass' else 2)
