"""Same-plane backland uses over finite original triangles; no height changes.

The public field, accepted precincts, all pending private courts and body holes
remain reserved. This stage does not manufacture missing ground or close banks.
"""
import collections,json,time,sys
from .build_scene import a,HERE,verify
from ...registered_topography.revisions.r17_district_batches import author as g
from ...registered_topography.revisions.public_corridors_r18 import public_domain

OUT=HERE/(sys.argv[1]if len(sys.argv)>1 else'backland_activation_r05')
SRC=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/backland_completion_r01'
PRIVATE=a.CITY/'registered_topography/revisions/r17_district_batches/contour_bulk_r01/effective_prepared_parcels_r03.json'
MASKS=a.CITY/'registered_topography/revisions/public_corridors_r18/boundary_ownership_inputs_r03.json'
NATIVE=SRC/'phase02_ownership_correction_r01/terrain_handoff.json'
RESERVATIONS=PRIVATE.parent/'physical_owner_handoff_r02.json'
PRIVATE20=a.CITY/'registered_topography/revisions/r17_district_batches/coherent_batch20_r01/top_scene_patch_r02.json'
def source_retirement_masks(scene, patch):
 result={}
 for row in patch['surface_edits']:
  key=(row['material'],row['triangle_index']);tri=scene['surfaces'][key[0]][3*key[1]:3*key[1]+3];poly=[[v[0],v[2]]for v in tri]
  if g.geo.polygon_area(poly)<=1e-10:continue
  plane=g.common.plane(tri)
  kept=[]
  for t in row['replacement_triangles_xyz_m']:
   if max(abs(v[1]-g.common.height(plane,[v[0],v[2]]))for v in t)>1e-7:raise ValueError('Private20 row includes changed-height replacements')
   kept.append([[v[0],v[2]]for v in t])
  result[key]=g.common.subtract([poly],kept)
 return result
def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def main():
 start=time.monotonic();OUT.mkdir(exist_ok=True);assert not(OUT/'surface_patch.json').exists()
 h=a.load(SRC/'terrain_handoff.json','dee7867fe7e368aa0c0e8f99b158d1177ee81fd3e632a77627afee3f2ef1ddcd')
 scene=verify(h['base_scene']);private=a.load(PRIVATE);cache=a.load(MASKS);native=a.load(NATIVE);reservations=a.load(RESERVATIONS,'9d3f4c559baea48c62e7d3405db44e73c4d69cf9207f3baea1d0f4bfed8a6ad1')
 private20=a.load(PRIVATE20,'08734236c487547ceedfcfc31bd34e6a2e68fd259b94d0b4da92153565695f28');priority=source_retirement_masks(scene,private20)
 feet=[p for r in native['native_footings']for p in r['polygons_xz_m']];fi=g.geo._SpatialIndex(8)
 for i,p in enumerate(feet):fi.add(i,p)
 for r in cache['source_refs']:verify(r)
 masks=[r['polygon_xz_m']for r in cache['masks']]+public_domain.polygons()
 for p in private['parcels']:masks+=p['whole_holding_polygons_xz_m']+p['walk_polygons_xz_m']
 for r in reservations['all_candidate_reservations']:
  masks.append(r['holding_polygon_xz_m']);masks+=r['external_route_polygons_xz_m']
 masks+=h['existing_access_reservations']+h['sealed_B15_routes']+h['current_city_route_reservations']
 idx=g.geo._SpatialIndex(8)
 for i,p in enumerate(masks):idx.add(i,p)
 groups=collections.defaultdict(list)
 for owner in h['material_owners']:
  for piece in owner['material_source_pieces']:
   # Private ground use cannot repaint an extant traffic or civic material.
   if piece['source_material']in ('road','alley','water','bank','space_civic'):continue
   groups[(piece['source_material'],piece['source_triangle_index'])].append((owner['id'],owner['named_owner'],piece))
 for r in g.TriangleIndex(scene,feet).rows:groups.setdefault((r['material'],r['triangle_index']),[])
 edits=[];append=collections.defaultdict(list);owners=collections.defaultdict(lambda:dict(area_m2=0.,pieces=0));proof=[];maxerr=0.;skipped=0;holearea=0.
 print('groups',len(groups),'masks',len(masks),flush=True)
 for number,((material,index),pieces)in enumerate(sorted(groups.items())):
  source=scene['surfaces'][material][index*3:index*3+3];sourcehash=g.canonical_sha(source);poly=[[v[0],v[2]]for v in source];plane=g.common.plane(source)
  blocked=[masks[i]for i in sorted(idx.candidates(poly))]+priority.get((material,index),[]);native_holes=g.common.disjoint_union([q for i in sorted(fi.candidates(poly))if(q:=g.clip(poly,feet[i]))]);claimed=list(native_holes);rows=[]
  for oid,named,piece in pieces:
   if piece['source_triangle_sha256']!=sourcehash:raise ValueError('Changed original backland triangle')
   candidate=g.clip(piece['polygon_xz_m'],poly)
   if not candidate:continue
   remaining=g.common.subtract([candidate],blocked+claimed)
   for q in remaining:
    if g.geo.polygon_area(q)<=1e-10:continue
    claimed.append(q);rows.append((oid,named,piece['target_material'],q))
  if not rows and not native_holes:skipped+=1;continue
  rest=g.common.subtract([poly],claimed);area=g.geo.polygon_area(poly);kept=sum(g.geo.polygon_area(q)for q in rest);owned=sum(g.geo.polygon_area(q)for q in claimed);error=abs(area-kept-owned);maxerr=max(maxerr,error)
  if error>1e-7:raise ValueError('Finite backland partition error '+str((material,index,error)))
  retained=[t for q in rest for t in g.fan_upward([[v[0],g.common.height(plane,v),v[1]]for v in q])]
  edits.append(dict(material=material,triangle_index=index,source_triangle_sha256=sourcehash,replacement_triangles_xyz_m=retained))
  for oid,named,target,q in rows:
   ts=list(g.fan_upward([[v[0],g.common.height(plane,v),v[1]]for v in q]));append[target].extend(v for t in ts for v in t);owners[(oid,named)]['area_m2']+=g.geo.polygon_area(q);owners[(oid,named)]['pieces']+=len(ts)
  cut_holes=sum(g.geo.polygon_area(q)for q in native_holes);holearea+=cut_holes
  proof.append(dict(material=material,triangle_index=index,original_area_m2=area,retained_area_m2=kept,reclassified_area_m2=owned-cut_holes,native_bottom_hole_area_m2=cut_holes,partition_error_m2=error))
  if number%4000==0:print('processed',number,'edits',len(edits),'seconds',time.monotonic()-start,flush=True)
 refs=[ref(SRC/'terrain_handoff.json'),ref(PRIVATE),ref(MASKS),ref(NATIVE),ref(RESERVATIONS),ref(PRIVATE20),ref(HERE/'author_backland_materials_r05.py')]+public_domain.source_refs()
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R8_SAME_PLANE_FUNCTIONAL_BACKLANDS',status='CANDIDATE_GROUND_MATERIAL_RECLASSIFICATION_ONLY',base_scene_sha256=h['base_scene']['sha256'],source_surface_hashes={m:g.canonical_sha(scene['surfaces'][m])for m in sorted({r['material']for r in edits})},surface_edits=edits,appended_surfaces=dict(append),removed_foundation_proxy_ids=[],source_references=refs)
 report=dict(schema='riverstone.r8.backland_material_partition.v2',source_refs=refs,source_owners=len(h['material_owners']),active_material_owners=len(owners),active_named_holdings=len({k[1]for k in owners}),reclassified_area_m2=sum(r['area_m2']for r in owners.values()),native_bottom_hole_area_m2=holearea,selected_native_instances=len(native['native_footings']),source_triangle_edits=len(edits),maximum_partition_error_m2=maxerr,private20_canonical_retirement_priority=True,private20_priority_source_rows=len(priority),unchanged_height_planes=True,unchanged_banks=True,missing_holes_filled=False,all_78_private_reservations_retained=True,owners=[dict(id=k[0],named_owner=k[1],**v)for k,v in sorted(owners.items())],source_partitions=proof,elapsed_s=time.monotonic()-start,limits=['Native fixtures require their separately verified active subset.','Unresolved retired-body holes remain unpainted; existing water, roads, courts and route corridors take priority.','Same-plane material use does not certify route traversal.'])
 for name,d in [('surface_patch.json',patch),('partition_review.json',report)]:(OUT/name).write_text(json.dumps(d,separators=(',',':'),allow_nan=False)+'\n')
 print({k:v for k,v in report.items()if k not in('owners','source_partitions','source_refs','limits')},flush=True)
if __name__=='__main__':main()
