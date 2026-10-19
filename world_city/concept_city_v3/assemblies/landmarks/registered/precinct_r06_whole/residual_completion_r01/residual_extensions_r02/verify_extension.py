"""Independent exact cross-pack, route and local-source closure for R02 extension."""
from pathlib import Path
import sys,json,time
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE));sys.path.insert(0,str(OUT.parent))
from resolve_pack import *
from retained_walks import RetainedWalkIndex
OUT=Path(__file__).resolve().parent

def polygons(row):return row.get('ribbon_polygons_xz_m',row.get('polygon_parts_xz_m',[row.get('polygon_xz_m')]))
def main():
 started=time.monotonic();pack=load(OUT/'resolved_extension_placements.json');protected=[];cache={};sources=[]
 def native(src,label):
  for p in src['placements']:
   cp=p['cache']['path']
   if cp not in cache:
    mesh=load(ROOT/cp);cache[cp]=roof_rectangles(mesh,{g['material']for g in mesh['groups']})[0]
   protected.extend({'id':p['id'],'kind':label+'_native','polygon_xz_m':b.xform(q,p)}for q in cache[cp])
 paths=[BASE/'resolved_connected_placements.json',OUT.parent/'resolved_residual_placements.json',CITY/'assemblies/landmarks/registered/precinct_r05_ground/phase02/resolved_placements.json',OUT.parent/'common_entry_repair_r02/resolved_placements.json']
 for path in paths:
  src=load(path);sources.append(ref(path));native(src,path.parent.name)
  protected.extend({'id':r.get('id',r.get('holding_id')),'kind':'shared_walk','polygon_xz_m':q}for r in src.get('internal_routes',[])+src.get('external_routes',[])for q in polygons(r)if q)
 wp=CITY/'assemblies/waterworks/registered_services_r01/locations.json';sources.append(ref(wp))
 for f in load(wp)['drawhouses']:
  protected.append({'id':f['id'],'kind':'water_native','polygon_xz_m':f['footprint_xz_m']});protected.extend({'id':f['id'],'kind':'shared_walk','polygon_xz_m':q}for q in f['walk_polygons_xz_m'])
 wp=CITY/'assemblies/waterworks/registered_mill_r01/interface_contract.json';sources.append(ref(wp));mill=load(wp);protected.append({'id':'mill','kind':'mill_native','polygon_xz_m':mill['site']['body_polygon_xz_m']});protected.extend({'id':'mill','kind':'shared_walk','polygon_xz_m':q}for q in mill['site']['walk_polygons_xz_m']);protected.append({'id':'mill_navigation','kind':'navigation','polygon_xz_m':mill['navigation_polygon_xz_m']})
 wp=CITY/'assemblies/waterworks/registered_water_completion_r01/crossing_interfaces.json';sources.append(ref(wp))
 for c in load(wp)['crossings']:
  for k,v in c.items():
   if 'polygon'in k and isinstance(v,list)and v and isinstance(v[0],list)and isinstance(v[0][0],(float,int)):protected.append({'id':c.get('id'),'kind':'crossing:'+k,'polygon_xz_m':v})
 wp=CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r02/public_handoff.json';sources.append(ref(wp));water=load(wp);protected.extend(dict(id=r['id'],kind='water_field',polygon_xz_m=q)for r in water['finite_field_owners']for q in r['polygons_xz_m']);protected.extend(dict(r,kind='water_deck')for r in water['native_deck_holes'])
 ix=geo._SpatialIndex(16)
 for i,r in enumerate(protected):ix.add(i,r['polygon_xz_m'])
 hits=[];shared=[];outside=[]
 for p in pack['placements']:
  cp=p['cache']['path']
  if cp not in cache:
   mesh=load(ROOT/cp);cache[cp]=roof_rectangles(mesh,{g['material']for g in mesh['groups']})[0]
  h=next(h for h in pack['holdings']if h['id']==p['holding_id']);hi=geo._SpatialIndex(8)
  for i,q in enumerate(polygons(h)):hi.add(i,q)
  for q in [b.xform(q,p)for q in cache[cp]]:
   missing=geo.polygon_area(q)-sum(geo.intersection_area(q,polygons(h)[i])for i in hi.candidates(q))
   if missing>1e-7:outside.append({'id':p['id'],'area_m2':missing})
   for i in ix.candidates(q):
    o=protected[i];ar=geo.intersection_area(q,o['polygon_xz_m'])
    if ar>1e-7:hits.append({'id':p['id'],'other_id':o['id'],'kind':o['kind'],'area_m2':ar})
 scene=terrain.load_scene();surface=RetainedWalkIndex(scene,[b.rect(*b.BOUNDS)]);sides=SideIndex(scene);routes=[]
 for r in pack['internal_routes']+pack['external_routes']:
  f=next(f for f in pack['holdings']if f['id']==r['holding_id']);ps=polygons(r);checks=[terrain.audit_polygon(surface,q,f['floor_y_m'])for q in ps];side=sides.audit([dict(id=r['id'],polygon_xz_m=q,floor_y_m=f['floor_y_m'])for q in ps]);rh=[]
  for q in ps:
   for i in ix.candidates(q):
    o=protected[i];ar=geo.intersection_area(q,o['polygon_xz_m'])
    if ar>1e-7:
     row=dict(id=r['id'],other_id=o['id'],kind=o['kind'],area_m2=ar)
     (shared if o['kind']=='shared_walk'else rh).append(row)
  routes.append(dict(id=r['id'],support_pass=all(c['passes_existing_surface']for c in checks),bank_contacts=side['contacts'],native_contacts=rh));hits+=rh
 refs=[];missing=[];mismatch=[];outsideproject=[]
 def scan(x):
  if isinstance(x,dict):
   if isinstance(x.get('path'),str)and'sha256'in x:
    refs.append(x);p=ROOT/x['path']
    if Path(x['path']).is_absolute()or'..'in Path(x['path']).parts:outsideproject.append(x)
    if not p.is_file():missing.append(x)
    elif sha(p)!=x['sha256']:mismatch.append(x)
   for v in x.values():scan(v)
  elif isinstance(x,list):
   for v in x:scan(v)
 for name in ('resolved_extension_placements.json','residual_surface_patch.json','combined_all_precinct_surface_patch.json','functional_field_domains.json'):scan(load(OUT/name))
 regen=[]
 for a in pack['assets']:
  source=load(ROOT/a['source']['path']);scan(source);compiled=coordinate_planes.compile_master(source,{'pitch':a['pitch_m']},max_candidate_cells=300000,max_output_cells=150000);fresh=render_data.make_render_data(compiled);regen.append(dict(id=a['id'],exact_cache_match=core.digest(fresh)==core.digest(load(ROOT/a['cache']['path']))))
 prior=load(OUT.parent/'combined_ready21_residual_surface_patch.json');combined=load(OUT/'combined_all_precinct_surface_patch.json')
 checks=dict(no_crosspack_contacts=not hits,no_native_outside_domain=not outside,all_routes_supported=all(r['support_pass']for r in routes),all_routes_bank_clear=not any(r['bank_contacts']for r in routes),all_local_references_valid=not(missing or mismatch or outsideproject),fresh_native_regeneration_exact=all(r['exact_cache_match']for r in regen),source_scene_unchanged=sha(terrain.SCENE_PATH)==terrain.SCENE_SHA256,ground_patch_pass=load(OUT/'residual_ground_tests.json')['status']=='PASS')
 report=dict(status='PASS'if all(checks.values())else'FAIL',checks=checks,sources=sources,summary=pack['summary'],crosspack_contacts=hits,native_outside_domain=outside,intentional_same_ground_walk_overlaps=shared,routes=routes,regeneration=regen,reference_records_checked=len(refs),missing=missing,mismatched=mismatch,outside_project=outsideproject,seconds=time.monotonic()-started,actual_composed_scene_or_runtime_replay=False)
 (OUT/'extension_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],checks,'refs',len(refs),'shared',len(shared),'seconds',report['seconds'],flush=True);assert report['status']=='PASS'
if __name__=='__main__':main()
