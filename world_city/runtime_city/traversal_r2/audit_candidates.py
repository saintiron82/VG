#!/usr/bin/env python3
"""Audit candidate physics without conflating near support with strict floor contact."""
import argparse,json,math
from pathlib import Path
import audit_report as baseline

def audit(prepared_path,report_path):
 p=json.loads(Path(prepared_path).read_text());r=json.loads(Path(report_path).read_text());out=baseline.audit(prepared_path,report_path)
 errors=out['errors'];results={x['id']:x for x in r.get('routes',[])}
 if p['schema']=='riverstone.city.r2_step_candidate_suite.v1':
  for id,result in results.items():
   error='False route pass: '+id
   if result.get('pass') and 'expected_failure' not in result and error in errors:
    if result['status']=='reached' and result['ground_ray_miss_frames']==0 and result['unsupported_flight_frames']==0 and result['non_fine_support_frames']==0:errors.remove(error)
   for step in result.get('step_samples',[]):
    if step['rise_m']>.152:errors.append('Step rise exceeds declared limit: '+id)
    if math.hypot(step['to'][0]-step['from'][0],step['to'][2]-step['from'][2])>4/60+.005:errors.append('Step moved too far: '+id)
  for id in ['NEGATIVE_STEP_TOO_HIGH_0P25','NEGATIVE_STEP_LOW_HEADROOM']:
   result=results.get(id,{})
   if not result.get('pass') or result.get('successful_steps')!=0:errors.append('Safety fixture was bypassed: '+id)
  out['contact_semantics']='Nearby support <=0.115m allowed; is_on_floor misses remain explicitly reported, not claimed as continuous physical contact.'
 if p['schema']=='riverstone.city.r2_source_grade_proxy_suite.v1':
  layer=json.loads(Path(p['sources']['topography']['path']).read_text());count=0
  for placement in layer['placements']:
   if placement['category']!='fine_walk_surface':continue
   asset=layer['assets'][placement['asset_key']];path=Path(p['repo_root'])/asset['render_path']
   if baseline.digest(path)!=asset['render_sha256']:errors.append('Visual cap used in proxy error measure changed: '+placement['id'])
   count+=1
  proxy_asset=next(a for a in p['assets'].values() if a.get('collision_format')=='source_grade_proxy_triangles')
  proxy=json.loads((Path(p['repo_root'])/proxy_asset['render_path']).read_text());bounds=proxy['bounds_xz_m']
  if count!=64:errors.append('Not all64 visual cap resources bound')
  if proxy['area_m2']!=1024:errors.append('Proxy area differs')
  area=0.
  for triangle in proxy['triangles']:
   a,b,c=triangle
   for x,y,z in triangle:
    if not(bounds[0]-1e-7<=x<=bounds[2]+1e-7 and bounds[1]-1e-7<=z<=bounds[3]+1e-7):errors.append('Proxy vertex outside finite bound')
   area+=abs((b[0]-a[0])*(c[2]-a[2])-(b[2]-a[2])*(c[0]-a[0]))/2
  if abs(area-1024)>1e-6:errors.append('Triangulated proxy area differs')
  if proxy['validation']['visual_sampled_column_count']!=102400 or proxy['validation']['max_source_proxy_vs_visual_center_error_m']>.0500001:errors.append('Proxy/visual bound failed')
  for id in ['NEGATIVE_AUTHORED_STEP_0P25','NEGATIVE_ACTUAL_SOLID_WALL','NEGATIVE_OUTSIDE_FINITE_PROXY','NEGATIVE_RIVER_HAS_NO_INFINITE_FLOOR']:
   if not results.get(id,{}).get('pass'):errors.append('Missing/failed proxy exclusion control: '+id)
  out['visual_resources_hash_verified']=count;out['proxy_validation']=proxy['validation']
 out['evidence_integrity']='verified' if not errors else 'invalid';return out
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--prepared',required=True);ap.add_argument('--report',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
 out=audit(a.prepared,a.report);Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));raise SystemExit(0 if out['evidence_integrity']=='verified' else 2)
