"""Finite public ownership only; preserve water, native decks and prior patches."""
import json,time,sys
from .height_field import HERE
from . import public_domain
from ..r17_district_batches import author as a,public_tails,side_clearance
from ..r17_district_batches.coherent_b15_r01 import compose_cluster

def read(path):return json.loads(path.read_bytes())
def input_masks(scene,binding_path=None):
 masks=[];refs=[]
 def addfile(path):
  refs.append(dict(path=str(path.relative_to(a.ROOT)),sha256=a.sha(path)));return read(path)
 binding_path=binding_path or a.CITY/'registered_integration/r8/district_bound_r04.json'
 binding=addfile(binding_path)
 patches=[]
 for row in binding['patches']:
  path=a.ROOT/row['path']
  if a.sha(path)!=row['sha256']:raise ValueError('Changed accepted patch '+row['path'])
  patches.append(path)
 for path in patches:
  patch=addfile(path)
  for r in patch['surface_edits']:
   t=scene['surfaces'][r['material']][r['triangle_index']*3:r['triangle_index']*3+3]
   if a.normal_y(t)<=1e-10 or side_clearance.physical_side(t,r['material']):continue
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
  for r in water['finite_field_owners']:
   for j,p in enumerate(r['polygons_xz_m']):masks.append(dict(id=r['id']+':'+str(j),polygon_xz_m=p))
  for r in water['native_deck_holes']:masks.append(dict(id=r['id'],polygon_xz_m=r['polygon_xz_m']))
 extra=public_domain.OUTER_PATH
 if extra.exists():
  d=addfile(extra);masks.extend(d.get('exclusions',[]))
 return masks,refs

def main():
 started=time.monotonic();scene=a.load_scene();source=HERE/(sys.argv[1]if len(sys.argv)>1 else'finite_field_candidate_r02.json');mesh=read(source);report=mesh['report']
 if report['schema']!='riverstone.r18.finite_public_emission.v2':raise ValueError('Expected audited direct finite emission')
 if report['max_cell_area_error_m2']>1e-8 or abs(report['owner_minus_rendered_area_m2'])>1e-8:raise ValueError('Finite coverage or render accounting hold')
 for r in report['source_refs']+[report['ownership_inputs'],report['source_mesh']]:
  if a.sha(a.ROOT/r['path'])!=r['sha256']:raise ValueError('Changed direct owner source')
 refs=report['source_refs']+[dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source))]
 exclusions=read(a.ROOT/report['ownership_inputs']['path'])['masks']
 owners=[dict(id=r['id'],polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m'],source_triangle_index=r['source_triangle_index'],kind='canonical_public_surface',material='road',action='field')for r in mesh['records']]
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
 # Keep the independently audited strictly positive fans rather than re-culling
 # sub-threshold numerical pieces through the older top helper.
 patch['appended_surfaces']['road']=[v for r in mesh['records']for t in r['triangles_xyz_m']for v in t]
 patch['id']='R18_CANONICAL_PUBLIC_CORRIDORS_CANDIDATE';patch['status']='CANDIDATE_PENDING_FINITE_SIDE_AND_BOUNDARY_REVIEW';patch['source_references']=refs
 patch['design_grade_exceptions']=dict(source=refs[-2]if len(refs)>1 else refs[-1],source_triangles=report['exception_source_triangles'],finite_area_m2=report['exception_area_m2'],actual_controller_gate='pending; authoring target exceptions are explicit')
 (HERE/'top_patch_candidate.json').write_text(json.dumps(patch,separators=(',',':'))+'\n');(HERE/'top_partition_review.json').write_text(json.dumps(dict(proof=proof,elapsed_s=time.monotonic()-started,activation=False),separators=(',',':'))+'\n');print('TOPS_READY',len(patch['surface_edits']),sum(len(v)//3 for v in patch['appended_surfaces'].values()),time.monotonic()-started,flush=True)
 # Closure is a separate bounded producer stage. Never activate the top-only
 # patch or suppress all old bank faces while waiting for that stage.
if __name__=='__main__':main()
