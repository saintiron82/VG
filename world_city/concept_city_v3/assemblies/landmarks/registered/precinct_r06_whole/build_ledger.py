"""Read actual native geometry and protected owner use. No scene writes."""
from pathlib import Path
import sys,json,math,hashlib,time,collections
import numpy as np
from scipy import ndimage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[5];CITY=ROOT/'world_city/concept_city_v3';sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_integration.r8.coverage_plan import build_plan as b
from world_city.concept_city_v3.assemblies.landmarks.registered.coverage_r5_draft_01.project_native import roof_rectangles
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as terrain
from world_city.runtime_city.checks import placement as geo
load=b.load;sha=b.sha;ref=b.ref

def write(n,d):(HERE/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def main():
 t=time.monotonic();scene=terrain.load_scene();source=load(CITY/'registered_integration/r8/coverage_plan/protected_source_owner_ledger.json');plan=load(CITY/'registered_source/plan.json');base=np.load(CITY/'registered_integration/r8/coverage_plan/baseline_masks.npz');used=np.zeros(b.SHAPE,bool);labels=np.zeros(b.SHAPE,np.uint8)
 for j,o in enumerate(source['owners'],1):
  m=b.mask([o['polygon_xz_m']],True)&~used;used|=m;labels[m]=j
 # Exact per-asset union of native horizontal faces at original pitch. This is
 # projected occupied geometry including roofs/courts, never an AABB substitute.
 existing=load(CITY/'registered_integration/r8/coverage_plan/native_projection.json')['assets'];assets={};native=np.zeros(b.SHAPE,bool);by_pack={};instances=[]
 relevant=[]
 for i in scene['common_instances']:
  a=scene['common_assets'][i['asset_key']];bb=a.get('bounds') or load(ROOT/a['render_path'])['bounds'];foot=b.xform(b.rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),i)
  if np.any(b.mask([foot])&used):relevant.append(i)
 for n,key in enumerate(sorted({i['asset_key']for i in relevant})):
  a=scene['common_assets'][key];mp,rp=ROOT/a['master_path'],ROOT/a['render_path'];assert sha(mp)==a['master_sha256']and sha(rp)==a['render_sha256'],key
  if key in existing:parts=existing[key]['native_owner_parts_local_xz_m'];proof=existing[key]['native_owner_projection_proof']
  else:
   mesh=load(rp);parts,proof=roof_rectangles(mesh,{g['material']for g in mesh['groups']})
  assets[key]={'source':ref(mp),'cache':ref(rp),'native_parts_local_xz_m':parts,'proof':proof}
  if n%20==0:print('assets',n,key,flush=True)
 for i in relevant:
  parts=[b.xform(p,i)for p in assets[i['asset_key']]['native_parts_local_xz_m']];m=b.mask(parts);native|=m;by_pack.setdefault(i['source_pack'],np.zeros(b.SHAPE,bool));by_pack[i['source_pack']]|=m
  instances.append({k:i[k]for k in('id','asset_key','source_pack','position_m','yaw_rad')}|{'native_parts_xz_m':parts})
 print('projected',len(assets),len(instances),flush=True)
 reservations=[]
 def reserve(id,kind,ps,path):
  if ps:reservations.append({'id':id,'kind':kind,'polygon_parts_xz_m':ps,'source':ref(path)})
 for phase in ('phase01','phase02'):
  path=CITY/f'assemblies/landmarks/registered/precinct_r05_ground/{phase}/resolved_placements.json';d=load(path)
  for h in d['holdings']:reserve(h['id'],phase,h['polygon_parts_xz_m'],path)
  for route in d.get('internal_routes',[]):reserve(route.get('id',route.get('holding_id','phase_route')),'retained_or_staged_access',route.get('ribbon_polygons_xz_m',[]),path)
 path=CITY/'assemblies/landscape/registered/resolved_placements.json';d=load(path)
 for s in d['sites']:
  if s.get('polygon_xz_m'):reserve(s['id'],'existing_designed_garden',[s['polygon_xz_m']],path)
 path=CITY/'assemblies/landmarks/registered/precinct_r04/resolved_placements.json';d=load(path)
 for f in d['productive_frames']:reserve(f['id'],'existing_productive_frame',f['logical_owned_floor_regions_xz_m'],path)
 for p in plan['paths']:
  reserve(p['id'],'existing_source_access',b.ribbon(p['polyline_xz_m'],max(2,p.get('width_m',2))+1),CITY/'registered_source/plan.json')
 # Independent accepted native pack paths remain protected even when not part of
 # the coarse registered path list.
 for relative,keys in [('assemblies/property/registered/r1/resolved_placements.json',['internal_routes','external_access_surfaces']),('assemblies/landscape/registered/training/resolved_placements.json',['internal_routes','external_access_surfaces']),('assemblies/landscape/registered/resolved_placements.json',['internal_routes','external_connections'])]:
  path=CITY/relative;d=load(path)
  for key in keys:
   for r in d.get(key,[]):
    ps=r.get('ribbon_polygons_xz_m',[])
    if not ps and r.get('polygon_xz_m'):ps=[r['polygon_xz_m']]
    if not ps and r.get('polyline_xz_m'):ps=b.ribbon(r['polyline_xz_m'],max(2,r.get('width_m',2))+1)
    reserve(r.get('id',key),'retained_native_access',ps,path)
 rmask=b.mask([p for r in reservations for p in r['polygon_parts_xz_m']],True);water=base['water'];public=base['road']
 rows=[]
 for j,o in enumerate(source['owners'],1):
  m=labels==j;remaining=m&~native&~rmask&~public&~water;cats={};left=m.copy()
  for key,mask in [('actual_native_geometry_projection',native),('preserved_functional_ground_or_access',rmask),('public_road',public),('water',water)]:
   q=left&mask;left&=~mask;cats[key]=b.area(q)
  cats['remaining_without_finite_implemented_use']=b.area(left)
  rows.append({'owner_id':o['source_owner_id'],'exclusive_whole_owner_grid_m2':b.area(m),'exclusive_within_blocks_grid_m2':b.area(m&(base['block_labels']>0)),'categories_disjoint_grid_m2':cats,'actual_native_pack_intersection_grid_m2':{k:b.area(m&v)for k,v in by_pack.items()if np.any(m&v)},'remaining_parts_xz_m':b.parts(left),'source_polygon_xz_m':o['polygon_xz_m'],'whole_owner_complete':False,'completion_note':'Native projection proves occupied geometry only, not usable/completed land. Existing functional grounds retained, phase02 only reserved. New use must have finite facilities and connected actual surface.'})
  print(o['source_owner_id'],cats,flush=True)
 write('actual_native_projection.json',{'scene':ref(terrain.SCENE_PATH),'assets':assets,'instances':instances,'method':'Actual native cached horizontal face union at its native lattice; rigid transform only. 1m center-sample disjoint owner accounting, exact native polygon pieces retained for checks.'})
 write('preserved_reservations.json',{'scene':ref(terrain.SCENE_PATH),'reservations':reservations})
 write('actual_owner_use_ledger.json',{'schema':'riverstone.precinct.r06.actual_owner_use_ledger.v1','scene':ref(terrain.SCENE_PATH),'source_owner_ledger':ref(CITY/'registered_integration/r8/coverage_plan/protected_source_owner_ledger.json'),'owners':rows,'summary':{'owners':len(rows),'within_block_area_m2':sum(x['exclusive_within_blocks_grid_m2']for x in rows),'remaining_grid_m2':sum(x['categories_disjoint_grid_m2']['remaining_without_finite_implemented_use']for x in rows),'actual_native_assets':len(assets),'actual_native_instances':len(instances),'seconds':time.monotonic()-t},'measurement':'Grid accounting is 1m center samples, not exact boolean area. Reservations and native polygons are retained separately. Nothing is automatically certified complete.'})
 np.savez_compressed(HERE/'owner_masks.npz',labels=labels,native=native,reserved=rmask,public=public,water=water,wall=base['wall'],bounds=b.BOUNDS,pitch=b.PITCH)
if __name__=='__main__':main()
