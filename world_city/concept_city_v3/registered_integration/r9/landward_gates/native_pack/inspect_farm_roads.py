"""Read-only review of producer-owned native farm/separator packs and public roads."""
import json,math
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import author as a
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_integration.r9.landward_gates.build_corridors import Ground
H=a.HERE.parent

def ccw(p):
 return p if sum(v[0]*w[1]-v[1]*w[0]for v,w in zip(p,p[1:]+p[:1]))>=0 else p[::-1]
def bb(p):return [min(v[0]for v in p),min(v[1]for v in p),max(v[0]for v in p),max(v[1]for v in p)]
def bo(p,q):return p[0]<q[2]+1e-9 and q[0]<p[2]+1e-9 and p[1]<q[3]+1e-9 and q[1]<p[3]+1e-9
def xz(v):return [v[0],v[2]]
def poly_for(i,b):return ccw([xz(a.world([x,0,z],i))for x,z in a.rect(b['min'][0],b['min'][2],b['max'][0],b['max'][2])])
def closest(p,poly):
 candidates=[]
 for q,r in zip(poly,poly[1:]+poly[:1]):
  dx,dz=r[0]-q[0],r[1]-q[1];den=dx*dx+dz*dz;t=max(0,min(1,((p[0]-q[0])*dx+(p[1]-q[1])*dz)/den))if den else 0
  v=[q[0]+t*dx,q[1]+t*dz];candidates.append((math.dist(p,v),v))
 return min(candidates)
def overlaps(poly,roads):
 pbb=bb(poly);hits=[]
 for side,j,q,qbb in roads:
  if not bo(pbb,qbb):continue
  cut=a.clip(poly,q);area=a.area(cut)
  if area>1e-8:hits.append({'side':side,'core_polygon_index':j,'overlap_area_m2':area,'overlap_polygon_xz_m':cut})
 return hits

def main():
 log=(H/'build_rerun5.log').read_text();assert 'READY' in log
 paths={n:H/n for n in ['farm_pack.json','routes.json','ground_ownership.json']};refs={n:a.ref(p)for n,p in paths.items()}
 farm=json.loads(paths['farm_pack.json'].read_text());routes=json.loads(paths['routes.json'].read_text());owners=json.loads(paths['ground_ownership.json'].read_text());assets={**a.S['common_assets'],**farm['common_assets']}
 roads=[]
 for owner in owners['owners']:
  if 'GATE_PUBLIC_CORRIDOR'not in owner['id']:continue
  for j,p in enumerate(owner['core_polygons_xz_m']):p=ccw(p);roads.append((owner['id'].split('_')[0],j,p,bb(p)))
 additions=[]
 for i in farm['add_instances']:
  b=assets[i['asset_key']].get('bounds',a.B.get(i['asset_key']));poly=poly_for(i,b);hits=overlaps(poly,roads)
  additions.append({'id':i['id'],'asset_key':i['asset_key'],'position_m':i['position_m'],'footprint_xz_m':poly,'native_y_range_m':[i['position_m'][1]+b['min'][1],i['position_m'][1]+b['max'][1]],'public_road_plan_overlaps':hits})
 training=[];top_quads=[]
 for id in ['TRAIN:r09:coarse','TRAIN:r09:fine']:
  i=a.I[id];asset=assets[i['asset_key']];path=a.ROOT/asset['render_path'];assert a.sha(path)==asset['render_sha256'];render=json.loads(path.read_text());hits=[];ny=set()
  for gn,g in enumerate(render['groups']):
   for qn,q in enumerate(g['quads']):
    u=[q[1][k]-q[0][k]for k in range(3)];v=[q[2][k]-q[0][k]for k in range(3)];normal_y=u[2]*v[0]-u[0]*v[2]
    if normal_y<1e-9:continue
    w=[a.world(v,i)for v in q];poly=ccw([xz(v)for v in w]);h=overlaps(poly,roads);ny.add(w[0][1]);r={'id':id,'group_index':gn,'quad_index':qn,'world_y_m':w[0][1],'polygon_xz_m':poly}
    top_quads.append(r)
    if h:hits.append(dict(r,public_road_plan_overlaps=h))
  training.append({'id':id,'asset':a.ref(path),'actual_native_top_elevations_m':sorted(ny),'road_top_overlaps':hits})
 ground=Ground(json.loads((H/'local_source_faces.json').read_text()));separators=[]
 for i in farm['add_instances']:
  if not i['id'].startswith('R9_WEST_PUBLIC_SEPARATOR'):continue
  p=xz(i['position_m']);b=assets[i['asset_key']]['bounds'];poly=poly_for(i,b);sup=[r for r in top_quads if geo.point_in_convex_polygon(p,r['polygon_xz_m'],1e-8)]
  native_overlap=[]
  for q in top_quads:
   if not bo(bb(poly),bb(q['polygon_xz_m'])):continue
   ar=a.overlap(poly,q['polygon_xz_m'])
   if ar>1e-8:native_overlap.append({'native_id':q['id'],'group_index':q['group_index'],'quad_index':q['quad_index'],'native_top_y_m':q['world_y_m'],'support_overlap_area_m2':ar})
  nearest=min((closest(p,q['polygon_xz_m'])[0],q['id'],q['group_index'],q['quad_index'],closest(p,q['polygon_xz_m'])[1],q['world_y_m'])for q in top_quads)
  try:ground_y=ground.at(p)
  except ValueError:ground_y=None
  separators.append({'id':i['id'],'position_m':i['position_m'],'native_bottom_world_y_m':i['position_m'][1]+b['min'][1],'native_top_at_actual_center':sup,'native_support_footprint_overlaps':native_overlap,'original_surface_ground_y_m':ground_y,'actual_center_ground_support_delta_m':i['position_m'][1]+b['min'][1]-ground_y if ground_y is not None else None,'nearest_native_top':{'distance_xz_m':nearest[0],'native_id':nearest[1],'group_index':nearest[2],'quad_index':nearest[3],'nearest_edge_xz_m':nearest[4],'top_world_y_m':nearest[5],'boundary_root_y_if_supported_here_m':nearest[5]-b['min'][1]}})
 print(json.dumps({'added_asset_road_overlap_ids':[r['id']for r in additions if r['public_road_plan_overlaps']],'training_top_road_overlap_counts':{r['id']:len(r['road_top_overlaps'])for r in training},'separators':len(separators),'separator_native_center_support_count':sum(bool(r['native_top_at_actual_center'])for r in separators),'separator_native_footprint_support_count':sum(bool(r['native_support_footprint_overlaps'])for r in separators),'separator_source_ground_supported_count':sum(r['actual_center_ground_support_delta_m']is not None and abs(r['actual_center_ground_support_delta_m'])<1e-8 for r in separators)},indent=2))
 report={'schema':'riverstone.city.landward_farm_road_diagnostic.v1','inputs':refs,'build_log':a.ref(H/'build_rerun5.log'),'scope':'Read-only exact native footprint/top-quad review against actual public road core polygons; no producer file edits. Plan overlap is reported separately from vertical collision.','additions':additions,'retained_training':training,'separators':separators,'native_training_elevation_note':'Native elevations are evaluated from frozen top quads. No fallback height is used. A nearby Y=18 surface does not imply the current separator lies on that native surface.'}
 name='farm_road_diagnostic_r01.json';out=a.HERE/name
 assert not out.exists(),'Keep existing diagnostic evidence; choose a new revision'
 a.write(name,report)
 for n,p in paths.items():assert a.sha(p)==refs[n]['sha256'],'Producer changed during inspection'
 print('REPORT',a.relative(out))

if __name__=='__main__':main()
