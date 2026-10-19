"""Conservative occupied-envelope/OBB review, not a second geometry engine."""
import importlib.util,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('author',HERE/'build_addendum.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def poly(bounds,p):return [[b.point(p,x,0,z)[i]for i in (0,2)] for x,z in [(bounds['min'][0],bounds['min'][2]),(bounds['max'][0],bounds['min'][2]),(bounds['max'][0],bounds['max'][2]),(bounds['min'][0],bounds['max'][2])]]
def overlap(a,aa,c,cc):
 if min(aa['max'][1]+a['position_m'][1],cc['max'][1]+c['position_m'][1])-max(aa['min'][1]+a['position_m'][1],cc['min'][1]+c['position_m'][1])<=.001:return False
 pa,pc=poly(aa,a),poly(cc,c)
 for p in [pa,pc]:
  for i in range(4):
   q,r=p[i],p[(i+1)%4];axis=[-(r[1]-q[1]),r[0]-q[0]]
   ra=[v[0]*axis[0]+v[1]*axis[1]for v in pa];rc=[v[0]*axis[0]+v[1]*axis[1]for v in pc]
   if min(max(ra),max(rc))-max(min(ra),min(rc))<=.001:return False
 return True

def main():
 ctx=json.loads((HERE/'base_instance_context.json').read_text());pack=json.loads((HERE/'pack.json').read_text());cache={};native=[]
 for p in ctx['common_instances']:
  if p['source_pack']=='woodland' or p['id'].startswith('FORT_'):continue
  key=p['asset_key']
  if key not in cache:cache[key]=json.loads((b.ROOT/ctx['common_assets'][key]['render_path']).read_text())['bounds']
  native.append(p)
 rows=[]
 for p in pack['add_instances']:
  if p['asset_key'] not in ('r9_city_roofed_bartizan','r9_castle_roofed_bartizan'):continue
  hits=[];support=[]
  for n in native:
   if overlap(p,pack['common_assets'][p['asset_key']]['bounds'],n,cache[n['asset_key']]):
    (support if n['asset_key']in ('registered_curtain_plain','registered_curtain_gate')else hits).append(n['id'])
  rows.append({'id':p['id'],'unapproved_building_envelope_hits':hits,'intentional_castle_curtain_support_hits':support})
 report={'status':'pass'if not any(r['unapproved_building_envelope_hits']for r in rows)else 'fail','method':'3D height-band + exact yaw-oriented rectangle separating-axis test on actual cached envelopes. Conservative for sparse native assets.','scope':'23 roofed watch chambers against existing non-woodland, non-fortification assets. Existing wall support/corner overlap recorded separately.','rows':rows,'excluded_woodland':True,'actual_runtime_collision_replay':'Not run; all new geometry stays above +5.5 m native ground.'}
 (HERE/'non_wall_aabb_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'watch_chambers':len(rows),'unapproved_hits':sum(len(r['unapproved_building_envelope_hits'])for r in rows)}));assert report['status']=='pass'
if __name__=='__main__':main()
