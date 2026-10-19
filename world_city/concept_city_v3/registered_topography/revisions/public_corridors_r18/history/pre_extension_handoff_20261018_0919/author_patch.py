"""Finite public ownership only; preserve water, native decks and prior patches."""
import json,time
from .height_field import HERE
from .survey import ROAD_IDS
from ..r17_district_batches import author as a,public_tails
from ..r17_district_batches.coherent_b15_r01 import compose_cluster

def read(path):return json.loads(path.read_bytes())
def input_masks(scene):
 masks=[];refs=[]
 def addfile(path):
  refs.append(dict(path=str(path.relative_to(a.ROOT)),sha256=a.sha(path)));return read(path)
 binding=addfile(a.CITY/'registered_integration/r8/civic_bound_r02.json')
 patches=[a.ROOT/r['path']for r in binding['patches']]
 # The residual producer explicitly supersedes the earlier ready21 patch.
 patches=[p for p in patches if p.name!='precinct_connected21_normalized_patch.json']
 patches.append(a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/combined_ready21_residual_surface_patch.json')
 b15=a.CITY/'registered_topography/revisions/r17_district_batches/coherent_b15_r01/candidate_scene_patch.json'
 if b15.exists():patches.append(b15)
 for path in patches:
  patch=addfile(path)
  for r in patch['surface_edits']:
   t=scene['surfaces'][r['material']][r['triangle_index']*3:r['triangle_index']*3+3]
   if a.normal_y(t)<=1e-10:continue
   poly=[[v[0],v[2]]for v in t];plane=a.common.plane(t)
   retained=[[[v[0],v[2]]for v in q]for q in r['replacement_triangles_xyz_m']if max(abs(v[1]-a.common.height(plane,[v[0],v[2]]))for v in q)<1e-8]
   masks.extend(dict(id=patch['id']+':'+str(r['triangle_index']),polygon_xz_m=q)for q in a.common.subtract([poly],retained))
 for r in scene['terrain_contract']['water_domain_polygons']:masks.append(dict(id='WET:'+r['surface_id'],polygon_xz_m=r['polygon_xz_m']))
 north=addfile(a.CITY/'assemblies/waterworks/registered_bridge/north_approach_r03/profile.json');b=north['bridge_frame']['basis'];t=north['bridge_frame']['translation']
 polygon=[]
 for x,z in[(-106,-3.125),(-64,-3.125),(-64,3.125),(-106,3.125)]:polygon.append([t[0]+b[0][0]*x+b[0][2]*z,t[2]+b[2][0]*x+b[2][2]*z])
 masks.append(dict(id='ACCEPTED_NORTH_NATIVE_CONNECTION',polygon_xz_m=polygon))
 path=a.CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r02/public_handoff.json'
 if path.exists():
  water=addfile(path)
  for r in water['finite_field_owners']+water['native_deck_holes']:
   masks.append(dict(id=r['id'],polygon_xz_m=r['polygon_xz_m']))
 extra=HERE/'fixed_interfaces.json'
 if extra.exists():
  d=addfile(extra);masks.extend(d.get('exclusions',[]))
 return masks,refs

def main():
 started=time.monotonic();scene=a.load_scene();plan=read(a.PLAN_PATH);mesh=read(HERE/'field_tessellation.json');assert not mesh['report']['held'];assert mesh['report']['height_code_sha256']==a.sha(HERE/'height_field.py')
 traffic=[];ti=a.geo._SpatialIndex(8)
 for r in plan['roads']:
  if r['id']not in ROAD_IDS:continue
  line=r['polyline_xz_m'];polys=[a.geo.road_ribbon(p,q,r['width_m'])for p,q in zip(line,line[1:])]+[public_tails.circle(p,r['width_m']/2)for p in line[1:-1]]
  for p in polys:ti.add(len(traffic),p);traffic.append(p)
 exclusions,refs=input_masks(scene);ei=a.geo._SpatialIndex(8)
 for i,r in enumerate(exclusions):ei.add(i,r['polygon_xz_m'])
 owners=[]
 for j,t in enumerate(mesh['triangles_xyz_m']):
  poly=[[v[0],v[2]]for v in t];parts=a.common.disjoint_union([q for i in ti.candidates(poly)if(q:=a.clip(poly,traffic[i]))]);parts=a.common.subtract(parts,[exclusions[i]['polygon_xz_m']for i in ei.candidates(poly)]);plane=a.common.plane(t)
  for k,p in enumerate(parts):owners.append(dict(id=f'PUBLIC_R18:{j}:{k}',polygon_xz_m=p,plane_y_xz_m=plane,kind='canonical_public_surface',material='road',action='field'))
 cap_path=a.CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json';caps=read(cap_path);allowed_holes=[];private=[]
 refs.append(dict(path=str(cap_path.relative_to(a.ROOT)),sha256=a.sha(cap_path)))
 for r in caps['records']:
  for j,c in enumerate(r['candidate_columns']):
   # Removing a whole coarse native column also removes its nontraffic part.
   # Restore that part at its exact old native cap datum; it is a private edge,
   # never an extra public walking width.
   allowed_holes.append(dict(old_terrain_body_hole_polygon_xz_m=c['polygon_xz_m']))
   y=max(v['world_y_interval_m'][1]for v in c['cells'])
   for k,p in enumerate(a.common.subtract([c['polygon_xz_m']],c['traffic_clip_polygons_xz_m'])):
    private.append(dict(id=f"{r['property_id']}:PRIVATE_CAP_RESTORATION:{j}:{k}",polygon_xz_m=p,plane_y_xz_m=[0,0,y],kind='nonwalking_private_cap_remainder',material='ground_stone',action='field'))
 owners+=private
 (HERE/'public_owners.json').write_text(json.dumps(dict(owners=owners,exclusion_refs=refs,excluded_domains=len(exclusions),private_cap_remainder_m2=sum(a.geo.polygon_area(r['polygon_xz_m'])for r in private)),separators=(',',':'))+'\n');print('owners',len(owners),'excluded',len(exclusions),'seconds',time.monotonic()-started,flush=True)
 patch,proof,index=compose_cluster.build(scene,owners,allowed_holes,[])
 patch['id']='R18_CANONICAL_PUBLIC_CORRIDORS_CANDIDATE';patch['status']='CANDIDATE_PENDING_FINITE_SIDE_AND_BOUNDARY_REVIEW';patch['source_references']=refs
 (HERE/'top_patch_candidate.json').write_text(json.dumps(patch,separators=(',',':'))+'\n');(HERE/'top_partition_review.json').write_text(json.dumps(dict(proof=proof,elapsed_s=time.monotonic()-started,activation=False),separators=(',',':'))+'\n');print('TOPS_READY',len(patch['surface_edits']),sum(len(v)//3 for v in patch['appended_surfaces'].values()),time.monotonic()-started,flush=True)
 # Closure is a separate bounded producer stage. Never activate the top-only
 # patch or suppress all old bank faces while waiting for that stage.
if __name__=='__main__':main()
