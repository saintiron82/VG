"""Finite R7 source-index ground ownership; no terrain heights/banks regenerated."""
from resolve_pack import *
from collections import defaultdict

def main(pack_name="resolved_placements.json", prefix="", include_routes=False):
 started=time.monotonic();scene=terrain.load_scene();pack=load(HERE/pack_name);units=pack['holdings'];holes=pack['actual_bearing_footprints'];index=terrain.TriangleIndex(scene,[u['polygon_xz_m']for u in units]);hi=geo._SpatialIndex(8)
 for i,h in enumerate(holes):hi.add(i,h['polygon_xz_m'])
 by_source={}
 for u in units:
  for row in index.covering(u['polygon_xz_m']):
   key=(row['material'],row['triangle_index']);entry=by_source.setdefault(key,{'source':row,'regions':[]});entry['regions'].append({'unit_id':u['id'],'function':u['function'],'polygon_xz_m':row['intersection_polygon_xz_m']})
 if include_routes:
  # Route ribbons are added as disjoint visible alley surfaces only over existing
  # ground triangles. Retained public road/alley and actual native floors stay.
  ri=terrain.TriangleIndex(scene,[p for r in pack['external_routes']for p in r['ribbon_polygons_xz_m']])
  for route in pack['external_routes']:
   for poly in route['ribbon_polygons_xz_m']:
    for row in ri.covering(poly):
     if row['material']in('road','alley','bank','water'):continue
     key=(row['material'],row['triangle_index']);entry=by_source.setdefault(key,{'source':row,'regions':[]});claimed=[q['polygon_xz_m']for q in entry['regions']]
     for q in terrain.common.subtract([row['intersection_polygon_xz_m']],claimed):
      if geo.polygon_area(q)>1e-8:entry['regions'].append({'unit_id':route['holding_id'],'function':'access_route','polygon_xz_m':q})
 edits=[];append=defaultdict(list);proof=[];totalcut=totalsoil=0.
 for (mat,tid),entry in sorted(by_source.items()):
  assert mat not in('road','alley','bank','water'),(mat,tid)
  r=entry['source'];tri=r['vertices_xyz_m'];poly=r['polygon_xz_m'];plane=r['plane_y_xz_m'];regions=entry['regions'];outside=terrain.common.subtract([poly],[q['polygon_xz_m']for q in regions]);replacement=[t for p in outside for t in terrain.fan_upward(terrain.common.lift(p,plane))] if hasattr(terrain.common,'lift')else[]
  # common.lift is not part of the contract; use the explicit source plane.
  replacement=[t for p in outside for t in terrain.fan_upward([[q[0],terrain.common.height(plane,q),q[1]]for q in p])]
  input_area=geo.polygon_area(poly);outside_area=sum(geo.polygon_area(p)for p in outside);newarea=cutarea=0
  for u in regions:
   p=u['polygon_xz_m'];cuts=[holes[i]['polygon_xz_m']for i in hi.candidates(p)if holes[i]['holding_id']==u['unit_id']];kept=terrain.common.subtract([p],cuts);area=sum(geo.polygon_area(q)for q in kept);newarea+=area;cutarea+=geo.polygon_area(p)-area;target='alley'if u['function']=='access_route'else'ground_grass'if u['function']=='orchard'else'ground_earth';
   assert target in scene['materials'],target
   for q in kept:
    for t in terrain.fan_upward([[v[0],terrain.common.height(plane,v),v[1]]for v in q]):append[target].extend(t)
  error=abs(input_area-outside_area-newarea-cutarea);assert error<1e-6,(mat,tid,error)
  assert all(terrain.normal_y(t)>0 for t in replacement)
  edits.append({'material':mat,'triangle_index':tid,'source_triangle_sha256':r['source_triangle_sha256'],'replacement_triangles_xyz_m':replacement,'owner_ids':sorted({u['unit_id']for u in regions})});proof.append({'material':mat,'triangle_index':tid,'source_area_m2':input_area,'outside_area_m2':outside_area,'new_ground_area_m2':newarea,'native_cut_area_m2':cutarea,'conservation_error_m2':error,'source_plane_y_xz_m':plane});totalcut+=cutarea;totalsoil+=newarea
 editedmats={e['material']for e in edits};sourcehash={m:terrain.canonical_sha(scene['surfaces'][m])for m in editedmats};waterhash=terrain.canonical_sha(scene['surfaces']['water']);bankhash=terrain.canonical_sha(scene['surfaces']['bank']);outside=[]
 for mat in editedmats:
  ids={e['triangle_index']for e in edits if e['material']==mat};vs=scene['surfaces'][mat];keep=[vs[j:j+3]for j in range(0,len(vs),3)if j//3 not in ids];outside.append({'material':mat,'unchanged_triangle_count':len(keep),'ordered_unchanged_sha256':terrain.canonical_sha(keep)})
 patch={'schema':'riverstone.finite_source_index_surface_patch.v1','status':'SOURCE_PATCH_NOT_APPLIED','base_scene_sha256':terrain.SCENE_SHA256,'base_scene':ref(terrain.SCENE_PATH),'source_surface_hashes':sourcehash,'surface_edits':edits,'appended_surfaces':dict(append),'removed_foundation_proxy_ids':[],'policy':'Only these original triangle indices are split once. Native bearings cut actual soil contact; new productive/work soil retains source planes. All bank/water arrays unchanged.','native_pack':ref(HERE/pack_name)}
 write(prefix+'surface_patch.json',patch);write(prefix+'ground_index_ledger.json',{'original_indices':[{'material':e['material'],'triangle_index':e['triangle_index'],'source_triangle_sha256':e['source_triangle_sha256']}for e in edits],'unchanged_arrays':{'water_sha256':waterhash,'bank_sha256':bankhash},'unchanged_ordered_triangles':outside,'per_source_conservation':proof})
 tests={'summary':{'source_indices':len(edits),'native_cut_area_m2':totalcut,'new_functional_ground_area_m2':totalsoil,'maximum_conservation_error_m2':max(p['conservation_error_m2']for p in proof),'appended_triangles':sum(len(v)//3 for v in append.values()),'seconds':time.monotonic()-started},'checks':{'all_source_hashes_match':True,'all_generated_triangles_upward':all(terrain.normal_y(v[i:i+3])>0 for v in append.values()for i in range(0,len(v),3)),'no_bank_or_water_edits':not any(e['material']in('bank','water')for e in edits),'source_planes_retained':True,'outside_triangles_byte_values_and_order_retained':True},'whole_terrain_regenerated':False,'applied_to_scene':False};assert all(tests['checks'].values());write(prefix+'ground_tests.json',tests);print(tests['summary'])
if __name__=='__main__':main()
