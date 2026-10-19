"""Bind the retained training native treads to their explicit public source seam."""
from pathlib import Path
import sys,json,math
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
from retained_walks import RetainedWalkIndex

def main():
 d=load(OUT/'training_entry_audit.json');source=load(BASE/'actual_native_projection.json');walk=load(BASE/'native_walk_support.json');special={r['id']:r for r in walk['instances']};bodies=[]
 for p in source['instances']:
  if p['asset_key']=='registered_training_r09_recovered_fine':continue # Its entire occupied height is <=.25m and all its actual top faces are the audited treads.
  ps=special[p['id']]['walking_body_parts_xz_m']if p['id']in special else p['native_parts_xz_m'];bodies.extend((p['id'],q)for q in ps)
 pack=load(BASE/'resolved_placements.json')
 for p in pack['placements']:
  mesh=load(ROOT/p['cache']['path']);bodies.extend((p['id'],b.xform(q,p))for q in slab_rectangles(mesh,.01,2.2))
 ix=geo._SpatialIndex(16)
 for i,(_,q)in enumerate(bodies):ix.add(i,q)
 contacts=[]
 for j,q in enumerate(d['polygon_parts_xz_m']):
  for i in ix.candidates(q):
   id,p=bodies[i];area=geo.intersection_area(q,p)
   if area>1e-7:contacts.append({'polygon_index':j,'native_id':id,'area_m2':area})
 seams=[];maxjump=0
 for c in d['checks']:
  ps=c['source_pieces']
  for r in ps:
   for q in r['polygon_xz_m']:
    ys=[terrain.common.height(t['plane_y_xz_m'],q)for t in ps if geo.point_in_convex_polygon(q,t['polygon_xz_m'],1e-7)]
    if ys:maxjump=max(maxjump,max(ys)-min(ys))
    if ys and max(ys)-min(ys)>.15+1e-7:seams.append({'point_xz_m':q,'height_jump_m':max(ys)-min(ys)})
 scene=terrain.load_scene();anchor=d['named_public_source_endpoint'];poly=d['actual_public_terminal_polygon_xz_m'];ti=terrain.TriangleIndex(scene,[poly]);actual=[r for r in ti.covering(poly)if r['material']in('road','alley')];sourceroad=next(r for r in load(CITY/'registered_source/plan.json')['roads']if r['id']==anchor['road_id']);publicparts=b.ribbon(sourceroad['polyline_xz_m'],sourceroad['width_m']);namedoverlap=sum(geo.intersection_area(poly,p)for p in publicparts);roadarea=sum(geo.polygon_area(r['intersection_polygon_xz_m'])for r in actual)
 seamheights=[]
 for q in anchor['seam_xyz_m']:
  vals=[terrain.common.height(r['plane_y_xz_m'],[q[0],q[2]])for r in ti.rows if geo.point_in_convex_polygon([q[0],q[2]],r['polygon_xz_m'],1e-7)]
  seamheights.append({'source_seam_xyz_m':q,'actual_top_y_m':vals,'minimum_delta_m':min([abs(y-q[1])for y in vals],default=None)})
 result={'sources':{'entry_audit':ref(OUT/'training_entry_audit.json'),'public_source_plan':ref(CITY/'registered_source/plan.json'),'native_projection':ref(BASE/'actual_native_projection.json')},'exact_native_body_contacts':contacts,'surface_seam_failures':seams,'maximum_actual_walk_step_m':maxjump,'source_public_road_id':anchor['road_id'],'source_public_segment_id':anchor['road_segment_id'],'named_public_ribbon_overlap_m2':namedoverlap,'actual_public_top_landing_area_m2':roadarea,'actual_public_triangle_ids':[r['triangle_index']for r in actual],'source_seam_actual_height_checks':seamheights,'runtime_capsule_replay':'not_run'}
 result['status']='PASS'if d['support_and_sides_pass']and not contacts and not seams and namedoverlap>0 and roadarea>0 else'BLOCKED';(OUT/'training_walk_tests.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],'contacts',len(contacts),'step',maxjump,'publictop',roadarea,'named',namedoverlap);print(contacts[:5])
if __name__=='__main__':main()
