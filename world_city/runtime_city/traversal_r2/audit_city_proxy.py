#!/usr/bin/env python3
"""Audit integrated proxy provenance, every finite tile, and retained actual controls."""
import argparse,json,math
from pathlib import Path
import audit_report as baseline

def audit(prepared,report):
 out=baseline.audit(prepared,report);p=json.loads(Path(prepared).read_text());errors=out['errors']
 manifest=json.loads(Path(p['sources']['city_proxy']['path']).read_text());verified=0
 for key,asset in manifest['assets'].items():
  path=Path(p['repo_root'])/asset['render_path']
  if baseline.digest(path)!=asset['render_sha256']:errors.append('Finite proxy tile changed: '+key)
  data=json.loads(path.read_text());bounds=data['bounds_xz_m']
  for triangle in data['triangles']:
   for x,y,z in triangle:
    if not bounds[0]-1e-7<=x<=bounds[2]+1e-7 or not bounds[1]-1e-7<=z<=bounds[3]+1e-7:errors.append('Triangle escaped owned finite tile '+key)
  verified+=1
 for key,asset in p.get('visual_ground_assets_replaced_for_collision',{}).items():
  if baseline.digest(Path(p['repo_root'])/asset['render_path'])!=asset['render_sha256']:errors.append('Visual comparison geometry changed: '+key)
 summary=manifest['summary']
 if summary['river_intersecting_source_tile_count']!=0:errors.append('River exclusion not established')
 if summary['body_void_intersection_area_m2']>1e-7:errors.append('Proxy covers body void')
 if summary['source_H_triangle_center_max_error_m']>1e-7:errors.append('Proxy deviates from exact source H')
 result=json.loads(Path(report).read_text());byid={v['id']:v for v in result['routes']}
 for id in ('NEGATIVE_CASTLE_WALL_IS_SOLID','NEGATIVE_RIVER_HAS_NO_INFINITE_FLOOR','NEGATIVE_AUTHORED_STEP_0P25'):
  if not byid.get(id,{}).get('pass'):errors.append('Missing/failed actual exclusion control: '+id)
 out['evidence_integrity']='verified' if not errors else 'invalid';out['all_finite_proxy_tile_hashes_verified']=verified
 out['proxy_summary']=summary;out['secondary_door_exception_buildings']=len(p.get('secondary_entrance_exceptions',[]))
 out['scope']='24fixedroutes only; optional finite owned-ground proxy; actual foundations/retaining/structures preserved; secondarydoor exceptions untested'
 return out
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--prepared',required=True);ap.add_argument('--report',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
 out=audit(a.prepared,a.report);Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));raise SystemExit(0 if out['evidence_integrity']=='verified' else 2)
