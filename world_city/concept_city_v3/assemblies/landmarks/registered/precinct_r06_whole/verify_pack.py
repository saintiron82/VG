"""Source/native/cache and finite cross-pack proof; no GUI or scene mutation."""
from resolve_pack import *

def main():
 start=time.monotonic();pack=load(HERE/'resolved_placements.json');projection=load(HERE/'actual_native_projection.json');units=pack['holdings'];owner=load(HERE/'actual_owner_use_ledger.json');opi={o['owner_id']:o['source_polygon_xz_m']for o in owner['owners']};polys=[(p['id'],q)for p in projection['instances']for q in p['native_parts_xz_m']];ix=geo._SpatialIndex(16)
 for i,(id,p)in enumerate(polys):ix.add(i,p)
 conflicts=[];containment=[]
 for u in units:
  p=u['polygon_xz_m'];sourceparts=b.triangulate(opi[u['owner_id']]);area=sum(geo.intersection_area(p,q)for q in sourceparts);containment.append({'id':u['id'],'area_m2':u['area_m2'],'owner_contained_area_m2':area,'pass':abs(area-u['area_m2'])<1e-6})
  for i in ix.candidates(p):
   id,q=polys[i];ar=geo.intersection_area(p,q)
   if ar>1e-7:conflicts.append({'unit_id':u['id'],'existing_native_id':id,'overlap_m2':ar})
 waterpath=CITY/'assemblies/waterworks/registered_services_r01/locations.json';water=load(waterpath);waterhits=[]
 for u in units:
  for f in water['drawhouses']:
   for kind,p in [('fixture',f['footprint_xz_m'])]+[('walk',p)for p in f['walk_polygons_xz_m']]:
    ar=geo.intersection_area(u['polygon_xz_m'],p)
    if ar>1e-8:waterhits.append({'holding_id':u['id'],'fixture_id':f['id'],'kind':kind,'area_m2':ar})
 regen=[]
 for a in load(HERE/'compiled_assets.json')['assets']:
  s=load(ROOT/a['source']['path']);old=load(ROOT/a['cache']['path']);c=coordinate_planes.compile_master(s,{'pitch':a['pitch_m']},max_candidate_cells=300000,max_output_cells=150000);mesh=render_data.make_render_data(c);same=core.digest(mesh)==core.digest(old);regen.append({'asset_id':a['id'],'source_hash_valid':sha(ROOT/a['source']['path'])==a['source']['sha256'],'cache_hash_valid':sha(ROOT/a['cache']['path'])==a['cache']['sha256'],'independent_common_regeneration_equal':same,'master_hash_bound':mesh['master_hash']==a['master_hash']});assert same,a['id']
 allrefs=[];missing=[];mismatch=[]
 def refs(x):
  if isinstance(x,dict):
   if 'path'in x and'sha256'in x and isinstance(x['path'],str):
    p=ROOT/x['path'];allrefs.append(x)
    if not p.is_file():missing.append(x)
    elif sha(p)!=x['sha256']:mismatch.append(x)
   for v in x.values():refs(v)
  elif isinstance(x,list):
   for v in x:refs(v)
 refs(pack)
 for a in pack['assets']:refs(load(ROOT/a['source']['path']))
 common=load(HERE/'native_preflight.json')['source_dependencies'];commonpass=all(sha(ROOT/r['path'])==r['sha256']for r in common)
 result={'source_scene_sha256':sha(terrain.SCENE_PATH),'expected_scene_sha256':terrain.SCENE_SHA256,'source_native_containment':containment,'existing_native_contacts':conflicts,'water_services':{'source':ref(waterpath),'contacts':waterhits},'independent_regeneration':regen,'dependency_checks':{'reference_records_checked':len(allrefs),'missing':missing,'mismatched':mismatch,'all_project_local':all(not Path(r['path']).is_absolute()for r in allrefs)},'common_source_files_unchanged':commonpass,'new_mesh_scaling':any(p['scale']!=[1,1,1]for p in pack['placements']),'actual_scene_modified':False,'seconds':time.monotonic()-start};result['pass']=not conflicts and not waterhits and all(x['pass']for x in containment)and all(all(v for k,v in r.items()if k!='asset_id')for r in regen)and not missing and not mismatch and commonpass and result['source_scene_sha256']==terrain.SCENE_SHA256;write('source_cache_tests.json',result);print('PASS',result['pass'],'nativecontacts',len(conflicts),'watercontacts',len(waterhits),'dependencies',len(allrefs),'sec',result['seconds']);assert result['pass']
if __name__=='__main__':main()
