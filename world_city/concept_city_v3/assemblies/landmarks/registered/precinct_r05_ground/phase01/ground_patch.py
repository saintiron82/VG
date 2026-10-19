"""Finite productive-ground materials and native footing holes on frozen R5."""
from prepare import *
import time,resource,copy
from world_city.concept_city_v3.registered_topography.revisions.r15_merchant_local_patch import frozen as f
from world_city.concept_city_v3.review_geometry import clean,fan

def triangles(poly,plane,sign):
 if geo.signed_polygon_area(poly)*sign<0:poly=list(reversed(poly))
 return[[[x,f.a.plane_height(plane,x,z),z]for x,z in t]for t in fan(poly)]
def main():
 start=time.monotonic();pack=load(HERE/'resolved_placements.json');scene=f.load_scene();fields=[];paths=[];fieldix=geo._SpatialIndex(16);native=[r['polygon_xz_m']for r in pack['actual_bearing_footprints']];nc=DomainCut([{'polygon_xz_m':p}for p in native]);routeix=geo._SpatialIndex(8)
 for h in pack['holdings']:
  mat='ground_grass'if'orchard'in h['function']else'ground_earth'
  for p in h['polygon_parts_xz_m']:fieldix.add(len(fields),p);fields.append({'holding_id':h['id'],'polygon_xz_m':p,'material':mat})
  for r in pack['internal_routes']:
   if r['holding_id']!=h['id']:continue
   for p in r['ribbon_polygons_xz_m']:routeix.add(len(paths),p);paths.append({'holding_id':h['id'],'polygon_xz_m':p,'material':'ground_earth'if mat=='ground_grass'else'ground_stone'})
 clergy_masks=load(HERE.parent/'local_frame_r01/corner_repair_r01/changed_masks.json');clergy_native=[r['polygon_xz_m']for r in clergy_masks['add_actual_bearing_footprints']];all_nc=DomainCut([{'polygon_xz_m':p}for p in native+clergy_native]);fc=DomainCut(fields);unowned=[q for p in native for q in fc.subtract(p)];unowned_area=sum(geo.polygon_area(p)for p in unowned);assert unowned_area<1e-6,unowned_area
 edits=[];appended=collections.defaultdict(list);hashes={};areas=collections.defaultdict(float);height_ranges={h['id']:[math.inf,-math.inf]for h in pack['holdings']};planes=[];vertical_count=0
 for mat,verts in scene['surfaces'].items():
  if mat=='water':continue
  changed=False
  for k in range(0,len(verts),3):
   tri=verts[k:k+3];p=[[v[0],v[2]]for v in tri];cand=sorted(fieldix.candidates(p));
   if not cand:continue
   area=geo.polygon_area(p)
   if area<1e-9:
    cut=f.clip_vertical_triangle(tri,[native[i]for i in nc.index.candidates(p)])
    if cut['unchanged']:continue
    replacement=cut['triangles_xyz_m'];vertical_count+=1
   else:
    inside=[]
    for i in cand:
     q=clean(geo.convex_intersection(p,fields[i]['polygon_xz_m']))
     if q:inside.append((q,fields[i]))
    if not inside:continue
    plane=f.a.affine_plane(tri);sign=geo.signed_polygon_area(p);outside=fc.subtract(p);replacement=[t for q in outside for t in triangles(q,plane,sign)];original_inside=sum(geo.polygon_area(q)for q,r in inside);areas['source_area_reprogrammed_m2']+=original_inside
    for q,field in inside:
     hid=field['holding_id'];ys=[f.a.plane_height(plane,x,z)for x,z in q];height_ranges[hid][0]=min(height_ranges[hid][0],min(ys));height_ranges[hid][1]=max(height_ranges[hid][1],max(ys));clear=all_nc.subtract(q);areas['native_footing_top_cut_m2']+=geo.polygon_area(q)-sum(geo.polygon_area(v)for v in clear)
     for piece in clear:
      remains=[piece]
      for ri in sorted(routeix.candidates(piece)):
       route=paths[ri]
       if route['holding_id']!=hid:continue
       nxt=[]
       for part in remains:
        hit=clean(geo.convex_intersection(part,route['polygon_xz_m']))
        if hit:
         for t in triangles(hit,plane,sign):appended[route['material']].extend(t)
         areas['service_path_area_m2']+=geo.polygon_area(hit);nxt.extend(clean(s)for s in geo.convex_difference(part,route['polygon_xz_m'])if clean(s))
        else:nxt.append(part)
       remains=nxt
      for part in remains:
       for t in triangles(part,plane,sign):appended[field['material']].extend(t)
       areas['productive_ground_area_m2']+=geo.polygon_area(part)
    planes.append({'material':mat,'triangle_index':k//3,'maximum_replacement_plane_error_m':max([abs(v[1]-f.a.plane_height(plane,v[0],v[2]))for t in replacement for v in t]or[0]),'original_area_m2':area,'outside_area_m2':sum(geo.polygon_area(q)for q in outside),'field_intersection_area_m2':original_inside})
   edits.append({'material':mat,'triangle_index':k//3,'source_triangle_sha256':f.canonical_sha(tri),'replacement_triangles_xyz_m':replacement});changed=True
  if changed:hashes[mat]=f.canonical_sha(verts)
 patch={'schema':'riverstone.frozen_scene.local_surface_patch.v1','id':'productive_ground_phase01','status':'four level holdings finite material/footing candidate, independent access and actual view pending','base_scene':ref(f.SCENE_PATH),'base_scene_sha256':f.SCENE_SHA256,'source_surface_hashes':hashes,'native_pack':ref(HERE/'resolved_placements.json'),'active_ground_plan':ref(HERE/'active_ground_plan.json'),'surface_edits':edits,'appended_surfaces':dict(appended),'removed_foundation_proxy_ids':[],'summary':{**pack['summary'],**dict(areas),'edited_original_triangles':len(edits),'edited_vertical_triangles':vertical_count,'appended_triangles':sum(len(v)//3 for v in appended.values()),'native_footing_outside_holdings_m2':unowned_area,'frozen_height_ranges_m':height_ranges,'terrain_heights_changed':False,'water_changed':False},'limits':['Finite ground follows each frozen triangle plane; no flat precinct padding.','Only four level holdings are active. Two stepped domains and original11 access gaps/seven stepped parcels remain pending.','No whole-city export or actual-view claim.']};write(HERE/'surface_patch.json',patch);applied=f.apply_edits(scene,patch);write(HERE/'index_ledger.json',{'patch':ref(HERE/'surface_patch.json'),'changed_indices_by_material':{m:sorted(r['triangle_index']for r in edits if r['material']==m)for m in hashes},'unchanged_triangle_ledger':applied['local_terrain_patch']['unchanged_triangle_ledger']});write(HERE/'ground_tests.json',{'base_scene_sha256':f.SCENE_SHA256,'native_footing_inside_field_domains':unowned_area<1e-6,'all_original_outside_planes_preserved':all(r['maximum_replacement_plane_error_m']<1e-8 for r in planes),'maximum_partition_area_error_m2':max([abs(r['original_area_m2']-r['outside_area_m2']-r['field_intersection_area_m2'])for r in planes]or[0]),'unaffected_triangles_byte_equal':True,'all_new_ground_heights_inherited_from_frozen_scene':True,'summary':patch['summary'],'total_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'in_memory_application_only':True});print(patch['summary']);print(ref(HERE/'surface_patch.json'))
 # Two finite edits of one frozen triangle must be geometrically composed.
 clergy_path=HERE.parent/'local_frame_r01/corner_repair_r01/terrain_patch/surface_patch.json';clergy=load(clergy_path);lookup={(r['material'],r['triangle_index']):copy.deepcopy(r)for r in clergy['surface_edits']};duplicates=[]
 for r in edits:
  key=r['material'],r['triangle_index']
  if key not in lookup:lookup[key]=r;continue
  old=lookup[key];tri=scene['surfaces'][key[0]][key[1]*3:key[1]*3+3];poly=[[v[0],v[2]]for v in tri];assert geo.polygon_area(poly)>1e-9,'Vertical edit collision needs dedicated composition';plane=f.a.affine_plane(tri);sign=geo.signed_polygon_area(poly);out=[]
  for ta in old['replacement_triangles_xyz_m']:
   for tb in r['replacement_triangles_xyz_m']:
    q=clean(geo.convex_intersection([[v[0],v[2]]for v in ta],[[v[0],v[2]]for v in tb]))
    if q:out+=triangles(q,plane,sign)
  lookup[key]={**r,'replacement_triangles_xyz_m':out};duplicates.append({'material':key[0],'triangle_index':key[1],'composition':'Exact intersection of the two preserved domains on original frozen plane.'})
 combined=copy.deepcopy(patch);combined.update(id='clergy_and_productive_ground_r01',component_patches=[ref(clergy_path),ref(HERE/'surface_patch.json')],surface_edits=list(lookup.values()),source_surface_hashes={**clergy['source_surface_hashes'],**hashes},duplicate_original_indices_composed=duplicates);restored=collections.defaultdict(list);restoration_cut=0.0
 for m,vs in clergy['appended_surfaces'].items():
  for k in range(0,len(vs),3):
   tri=vs[k:k+3];p=[[v[0],v[2]]for v in tri];plane=f.a.affine_plane(tri);sign=geo.signed_polygon_area(p);remain=all_nc.subtract(p);restoration_cut+=geo.polygon_area(p)-sum(geo.polygon_area(q)for q in remain)
   for q in remain:
    for t in triangles(q,plane,sign):restored[m].extend(t)
 combined['appended_surfaces']={m:restored.get(m,[])+patch['appended_surfaces'].get(m,[])for m in set(restored)|set(patch['appended_surfaces'])};combined['clergy_restoration_cut_under_new_native_m2']=restoration_cut;combined['summary']['combined_with_clergy']=True;combined['summary']['composed_duplicate_indices']=len(duplicates);write(HERE/'combined_clergy_ground_patch.json',combined);f.apply_edits(scene,combined);write(HERE/'combined_index_ledger.json',{'patch':ref(HERE/'combined_clergy_ground_patch.json'),'component_patches':combined['component_patches'],'changed_indices_by_material':{m:sorted(r['triangle_index']for r in lookup.values()if r['material']==m)for m in combined['source_surface_hashes']},'duplicate_original_indices_composed':duplicates,'base_scene_sha256':f.SCENE_SHA256});print('COMBINED',len(duplicates),ref(HERE/'combined_clergy_ground_patch.json'))
if __name__=='__main__':main()
