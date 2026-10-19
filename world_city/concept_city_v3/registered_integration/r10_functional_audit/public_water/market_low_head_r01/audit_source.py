"""Exact finite source audit of the independent low-head market proposal."""
import json,math
from pathlib import Path
from ..author import B,R,S,SHA,ref,load,sha
from ..select_sites import rect,trans
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches.side_clearance import SideIndex
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.registered_source.geometry import triangulate
H=Path(__file__).resolve().parent
scene=load(S);assert sha(S)==SHA;candidates=load(H/'candidate_screen.json')['first_candidates'];ix=a.TriangleIndex(scene,[p for r in candidates for p in [r['footprint_xz_m'],r['branch_polygon_xz_m']]]);side=SideIndex(scene,[p for r in candidates for p in [r['footprint_xz_m'],r['branch_polygon_xz_m']]])
assets=load(B/'registered_integration/r9/landward_gates/asset_bounds.json');instances={i['id']:i for i in scene['common_instances']}
for rr in load(B/'registered_integration/r9/integration_r02/index.json')['packs']:
 p=load(R/rr['path']);assets.update({k:v['bounds']for k,v in p.get('common_assets',{}).items()})
 for x in p.get('remove_instance_ids',[]):instances.pop(x,None)
 for r in p.get('add_instances',[]):instances[r['id']]=r
 for r in p.get('replace_instances',[]):instances[r['id']]=dict(instances[r['id']],asset_key=r['asset_key'])
obs=[];oi=g._SpatialIndex(8)
for p in instances.values():
 bb=assets[p['asset_key']];q=trans(rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),p['position_m'],p.get('yaw_rad',0));oi.add(len(obs),q);obs.append(dict(id=p['id'],poly=q,lo=p['position_m'][1]+bb['min'][1],hi=p['position_m'][1]+bb['max'][1]))
for p in scene.get('boxes',[]):
 ss=p['size_m'];q=trans(rect(-ss[0]/2,-ss[2]/2,ss[0]/2,ss[2]/2),p['position_m'],p.get('yaw_rad',0));oi.add(len(obs),q);obs.append(dict(id=p['id'],poly=q,lo=p['position_m'][1]-ss[1]/2,hi=p['position_m'][1]+ss[1]/2))
plan=load(B/'registered_source/plan.json');out=[]
for r in candidates:
 ground=a.audit_polygon(ix,r['footprint_xz_m'],4);access=a.audit_polygon(ix,r['branch_polygon_xz_m'],4);owners=[dict(id=str(i),polygon_xz_m=p['polygon_xz_m'],plane_y_xz_m=p['plane_y_xz_m'])for i,p in enumerate(ground['source_pieces']+access['source_pieces'])];banks=side.audit(owners);hits=[]
 for key in ['footprint_xz_m','branch_polygon_xz_m']:
  q=r[key]
  hits.extend(dict(kind=key,id=obs[j]['id'])for j in oi.candidates(q)if obs[j]['hi']>4.00001 and obs[j]['lo']<6.2 and g.polygon_area(g.convex_intersection(q,obs[j]['poly']))>1e-7)
 prop=[]
 for p in plan['plots']:
  if not p.get('polygon_xz_m'):continue
  area=sum(g.polygon_area(g.convex_intersection(r['footprint_xz_m'],t))+g.polygon_area(g.convex_intersection(r['branch_polygon_xz_m'],t))for t in triangulate(p['polygon_xz_m']))
  if area>1e-7:prop.append(dict(id=p['id'],area_m2=area))
 road=sum(v['area_m2']for v in ground['source_pieces']if v['material']in ['road','alley']);valid=ground['passes_existing_surface']and access['passes_existing_surface']and not banks['contacts']and not hits and not prop and road<1e-7
 out.append(dict(candidate=r,status='PASS_FINITE_SOURCE_SCREEN'if valid else'REJECT',ground=ground,access=access,bank_audit=banks,native_or_legacy_bound_hits=hits,registered_plot_hits=prop,actual_road_area_under_pocket_m2=road))
 if valid:break
result=dict(status='PASS_SELECTED_FINITE_CANDIDATE'if out and out[-1]['status']=='PASS_FINITE_SOURCE_SCREEN'else'NO_FINITE_CANDIDATE',base_scene=ref(S),source_plan=ref(B/'registered_source/plan.json'),candidate_screen=ref(H/'candidate_screen.json'),native_instances_checked=len(instances),legacy_boxes_checked=len(scene.get('boxes',[])),results=out,activation=False,still_required=['Low-head basin native authoring/compile','Finite owner patch and source conflict test','Runtime, integrated visual review, hydraulic/source-quality design'])
(H/'source_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],[(x['status'],x['candidate']['position_m'],x['actual_road_area_under_pocket_m2'])for x in out])
