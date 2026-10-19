import json,collections
from .prepare import HERE,load,write,ref
from .. import author as a,native_clearance

def run():
 report=json.loads((HERE/'top_coverage_report_r01.json').read_bytes());hand=json.loads((HERE/'physical_owner_handoff_r02.json').read_bytes());byid={r['id']:r for r in hand['rendered_plane_owners']};fails=[r for r in report['failures']if r['outside_cut_domain_m2']>1e-7];windows=[p for r in fails for p in r['outside_cut_polygons_xz_m']];binding=json.loads((HERE/'side_context_binding.json').read_bytes());scene=load(binding['current_scene']);idx=a.TriangleIndex(scene,windows);projection=json.loads(native_clearance.PROJECTION.read_bytes());native=[];ni=a.geo._SpatialIndex(8);retired=set(json.loads((HERE/'native_pack_ready_r02.json').read_bytes())['replaced_placement_ids']);
 for r in projection['instances']:
  if r['id'] in retired:continue
  for p in r['native_owner_parts_xz_m']:ni.add(len(native),p);native.append(dict(id=r['id'],polygon_xz_m=p))
 rows=[];groups=collections.defaultdict(lambda:dict(source_area_m2=0,covered_current_top_m2=0,missing_current_top_m2=0,max_difference_m=0,materials=collections.Counter(),native=collections.Counter()))
 for f in fails:
  owner=byid[f['id']];r=dict(id=f['id'],holding_id=f['holding_id'],pieces=[])
  for p in f['outside_cut_polygons_xz_m']:
   covers=list(idx.covering(p));remaining=a.common.subtract([p],[c['intersection_polygon_xz_m']for c in covers]);contacts=[]
   for j in ni.candidates(p):
    q=a.clip(p,native[j]['polygon_xz_m'])
    if q and a.geo.polygon_area(q)>1e-8:contacts.append(dict(native_id=native[j]['id'],area_m2=a.geo.polygon_area(q),polygon_xz_m=q))
   g=groups[f['holding_id']];g['source_area_m2']+=a.geo.polygon_area(p);g['missing_current_top_m2']+=sum(a.geo.polygon_area(q)for q in remaining)
   for c in covers:
    ar=a.geo.polygon_area(c['intersection_polygon_xz_m']);g['covered_current_top_m2']+=ar;g['materials'][c['material']]+=ar;g['max_difference_m']=max(g['max_difference_m'],max(abs(a.common.height(c['plane_y_xz_m'],v)-a.common.height(owner['plane_y_xz_m'],v))for v in c['intersection_polygon_xz_m']))
   for c in contacts:g['native'][c['native_id']]+=c['area_m2']
   r['pieces'].append(dict(polygon_xz_m=p,current_top_pieces=covers,missing_current_top_polygons_xz_m=remaining,retained_native_projection_contacts=contacts))
  rows.append(r)
 for g in groups.values():g['materials']=dict(g['materials']);g['native']=dict(g['native'])
 write('actual_public_fringe_review_r01.json',dict(current_scene=binding['current_scene'],rows=rows,summary=dict(groups)));print(json.dumps(groups,indent=2),flush=True)
if __name__=='__main__':run()
