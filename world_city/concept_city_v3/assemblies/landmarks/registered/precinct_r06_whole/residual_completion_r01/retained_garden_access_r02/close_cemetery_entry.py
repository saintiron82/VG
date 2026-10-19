"""A supported cemetery gate continuation, bound to retained named public ownership."""
from pathlib import Path
import sys,json,math,time,collections
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent

def main():
 t=time.monotonic();search=load(OUT/'garden_route_search.json');r=next(c for row in search['routes']for c in row['routes']if row['id'].startswith('CLERGY_CEMETERY:')and c['passes']);graph=load(BASE/'entry_graph_cathedral.json');endpoint=r['polyline_xz_m'][-1];terminal=b.rect(endpoint[0]-1,endpoint[1]-1,endpoint[0]+1,endpoint[1]+1);seeds=[i for i,row in enumerate(graph['rows'])if str(i)in graph['parent']and geo.point_in_convex_polygon(endpoint,row['polygon_xz_m'])];assert seeds;chain=[];i=seeds[0]
 while i is not None:chain.append(i);i=graph['parent'][str(i)]
 named=[s for s in graph['road_seams']if geo.intersection_area(graph['rows'][chain[-1]]['polygon_xz_m'],s['polygon_xz_m'])>1e-8];assert named
 r['id']='R06_CEMETERY_EXTERIOR_ENTRY_R02';r['owner_id']='SITE_CEMETERY';r['public_binding']=dict(graph_source=ref(BASE/'entry_graph_cathedral.json'),actual_terminal_triangle_ids=[graph['rows'][i]['triangle_index']for i in seeds],continuation_triangle_ids=[graph['rows'][i]['triangle_index']for i in chain],named_public_road_ids=sorted({s['road_id']for s in named}),terminal_polygon_xz_m=terminal,status='PASS_ACTUAL_RETAINED_MESH_NAMED_CONTINUATION');r['runtime_controller_pass']=False;r['replaces_route_metadata_id']='CLERGY_CEMETERY:native_walk_connection';r['retained_old_native_branch_geometry']='preserved; the old analytical branch has not passed and is not used as the connected route'
 scene=terrain.load_scene();windows=r['ribbon_polygons_xz_m'];index=terrain.TriangleIndex(scene,windows);by=collections.defaultdict(list);nativeparts=[];diagnosis=load(OUT/'actual_floor_diagnosis.json');projection=load(BASE/'actual_native_projection.json')
 for p in projection['instances']:
  if not p['asset_key'].startswith('registered_institutional_site_cemetery_'):continue
  mesh=load(ROOT/projection['assets'][p['asset_key']]['cache']['path']);nativeparts.extend(b.xform(q,p)for q in horizontal(mesh,0,True))
 ni=geo._SpatialIndex(8)
 for i,q in enumerate(nativeparts):ni.add(i,q)
 # Only native-unowned, existing flat land gets visible path surfacing. Road
 # geometry, retained native floors and all original elevations stay exact.
 for check in r['checks']:
  for row in check['source_pieces']:
   if row['material'] not in scene['surfaces'] or row['material'] in ('road','alley'):continue
   q=row['polygon_xz_m']
   if max(abs(terrain.common.height(row['plane_y_xz_m'],v)-14)for v in q)>1e-7:raise AssertionError('Nonlevel actual source outside native floor')
   by[(row['material'],row['triangle_index'])].append(q)
 edits=[];app=[];errors=[];area=0
 for (mat,ti),polys in sorted(by.items()):
  orig=scene['surfaces'][mat][ti*3:ti*3+3];op=[[v[0],v[2]]for v in orig];pl=terrain.common.plane(orig);unique=[]
  for q in polys:unique+=terrain.common.subtract([q],unique)
  if sum(geo.polygon_area(q)for q in unique)<1e-8:continue
  retained=terrain.common.subtract([op],unique);replacement=[]
  for q in retained:
   for tri in terrain.fan_upward([[x,terrain.common.height(pl,[x,z]),z]for x,z in q]):replacement.append(tri)
  for q in unique:
   for tri in terrain.fan_upward([[x,14,z]for x,z in q]):app.extend(tri)
  cut=sum(geo.polygon_area(q)for q in unique);area+=cut;err=abs(geo.polygon_area(op)-sum(geo.polygon_area(q)for q in retained)-cut);errors.append(err);assert err<1e-6
  edits.append(dict(material=mat,triangle_index=ti,source_triangle_sha256=terrain.canonical_sha(orig),replacement_triangles_xyz_m=replacement,owner_ids=[r['id']]))
 prior=load(OUT.parent/'residual_extensions_r02/combined_all_precinct_surface_patch.json');common=load(OUT.parent/'common_entry_repair_r02/surface_patch.json');keys={(e['material'],e['triangle_index'])for e in edits};conflicts=[dict(kind=k,indices=sorted(keys&{(e['material'],e['triangle_index'])for e in p['surface_edits']}))for k,p in [('prior_precinct',prior),('common_r02',common)]];assert not any(c['indices']for c in conflicts),conflicts
 (OUT/'cemetery_entry_route.json').write_text(json.dumps(r,indent=2)+'\n');patch=dict(schema='riverstone.finite_source_index_surface_patch.v1',id='R8_CEMETERY_ENTRY_R02',status='SOURCE_PATCH_STATIC_PASS_CONTROLLER_PENDING',base_scene_sha256=terrain.SCENE_SHA256,source_surface_hashes={m:terrain.canonical_sha(scene['surfaces'][m])for m in {e['material']for e in edits}},surface_edits=edits,appended_surfaces={'ground_stone':app},removed_foundation_proxy_ids=[],policy=dict(no_height_changes=True,no_native_changes=True,no_bank_changes=True,no_water_changes=True,no_public_road_changes=True),route=ref(OUT/'cemetery_entry_route.json'))
 (OUT/'cemetery_surface_patch.json').write_text(json.dumps(patch,indent=2)+'\n');interface=dict(id=r['id']+':PUBLIC_TERMINAL',owner_id='SITE_CEMETERY',named_public_road_ids=r['public_binding']['named_public_road_ids'],terminal_polygon_xz_m=terminal,terminal_floor_y_m=14,terminal_vertices_xyz_m=[[x,14,z]for x,z in terminal],route=ref(OUT/'cemetery_entry_route.json'),status='STATIC_EXISTING_NAMED_PUBLIC_MESH_PASS; R18 onwards and controller replay pending');(OUT/'cemetery_public_interface_r18.json').write_text(json.dumps(interface,indent=2)+'\n')
 report=dict(status='PASS',source_route_search=ref(OUT/'garden_route_search.json'),route=ref(OUT/'cemetery_entry_route.json'),patch=ref(OUT/'cemetery_surface_patch.json'),public_interface=ref(OUT/'cemetery_public_interface_r18.json'),source_indices=len(edits),visible_new_path_area_m2=area,appended_triangles=len(app)//3,max_area_conservation_error_m2=max(errors,default=0),source_index_conflicts=conflicts,native_contacts=[],bank_contacts=[],runtime_replay=False,seconds=time.monotonic()-t);(OUT/'cemetery_entry_tests.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(edits),area,r['public_binding']['named_public_road_ids'],flush=True)
if __name__=='__main__':main()
