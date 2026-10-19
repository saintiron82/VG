"""Finite original-index residual patch and collision-safe composition with ready21."""
from pathlib import Path
import sys,json,time,collections
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent

def parts(u):return u.get('polygon_parts_xz_m',[u.get('polygon_xz_m')])
def lift(p,plane):return [[q[0],terrain.common.height(plane,q),q[1]]for q in p]
def main():
 t=time.monotonic();scene=terrain.load_scene();packpath=OUT/'resolved_extension_placements.json';pack=load(packpath);oldpath=OUT.parent/'combined_ready21_residual_surface_patch.json';old=load(oldpath);ready=load(BASE/'resolved_connected_placements.json');prior=load(OUT.parent/'resolved_residual_placements.json');ready['holdings']+=prior['holdings'];ready['external_routes']+=prior['external_routes'];priority=[q for h in ready['holdings']for q in parts(h)]+[q for r in ready['external_routes']for q in r['ribbon_polygons_xz_m']];pi=geo._SpatialIndex(16)
 for i,q in enumerate(priority):pi.add(i,q)
 domains=[]
 for r in pack['external_routes']+pack['internal_routes']:
  for q in r.get('ribbon_polygons_xz_m',r.get('polygon_parts_xz_m',[])):domains.append({'owner_id':r['holding_id'],'function':'access_route','polygon_xz_m':q})
 for h in pack['holdings']:
  if h.get('ground_material_policy')=='retain_original_source_ground_except_visible_inspection_path':continue
  for q in parts(h):domains.append({'owner_id':h['id'],'function':h['function'],'polygon_xz_m':q})
 index=terrain.TriangleIndex(scene,[r['polygon_xz_m']for r in domains]);by_source={};skip=collections.Counter()
 for d in domains:
  for p in terrain.common.subtract([d['polygon_xz_m']],[priority[i]for i in pi.candidates(d['polygon_xz_m'])]):
   for r in index.covering(p):
    if geo.polygon_area(r['polygon_xz_m'])<=1e-8:continue
    if r['material']in('road','alley','bank','water'):skip[r['material']]+=geo.polygon_area(r['intersection_polygon_xz_m']);continue
    key=(r['material'],r['triangle_index']);e=by_source.setdefault(key,{'source':r,'regions':[]});claimed=[q['polygon_xz_m']for q in e['regions']]
    for q in terrain.common.subtract([r['intersection_polygon_xz_m']],claimed):
     if geo.polygon_area(q)>1e-8:e['regions'].append({'owner_id':d['owner_id'],'function':d['function'],'polygon_xz_m':q})
 holes=pack['actual_bearing_footprints'];hi=geo._SpatialIndex(8)
 for i,h in enumerate(holes):hi.add(i,h['polygon_xz_m'])
 edits=[];append=collections.defaultdict(list);proof=[];totalcut=totalground=0
 for (mat,tid),e in sorted(by_source.items()):
  if not e['regions']:continue
  r=e['source'];plane=r['plane_y_xz_m'];poly=r['polygon_xz_m'];owned=[q['polygon_xz_m']for q in e['regions']];outside=terrain.common.subtract([poly],owned);replacement=[tri for p in outside for tri in terrain.fan_upward(lift(p,plane))];a0=geo.polygon_area(poly);ao=sum(geo.polygon_area(p)for p in outside);new=cut=0
  for q in e['regions']:
   p=q['polygon_xz_m'];kept=terrain.common.subtract([p],[holes[i]['polygon_xz_m']for i in hi.candidates(p)]);area=sum(geo.polygon_area(p)for p in kept);new+=area;cut+=geo.polygon_area(p)-area;target='alley'if q['function']=='access_route'else'ground_grass'if any(k in q['function']for k in('orchard','quiet_garden'))else'ground_earth';assert target in scene['materials']
   for p in kept:
    for tri in terrain.fan_upward(lift(p,plane)):append[target].extend(tri)
  err=abs(a0-ao-new-cut)
  if err>=1e-6:(OUT/'failed_partition_diagnostic.json').write_text(json.dumps({'material':mat,'index':tid,'entry':e,'outside':outside,'source_area':a0,'outside_area':ao,'new_area':new,'cut':cut,'error':err},indent=2))
  assert err<1e-6,(mat,tid,err);edits.append({'material':mat,'triangle_index':tid,'source_triangle_sha256':r['source_triangle_sha256'],'replacement_triangles_xyz_m':replacement,'owner_ids':sorted({q['owner_id']for q in e['regions']})});proof.append({'material':mat,'triangle_index':tid,'source_area_m2':a0,'outside_area_m2':ao,'new_ground_area_m2':new,'native_cut_area_m2':cut,'conservation_error_m2':err,'source_plane_y_xz_m':plane,'owned_regions':e['regions']});totalcut+=cut;totalground+=new
 mats={e['material']for e in edits};patch={'id':'R8_PRECINCT_EXTENDED_INSPECTION_PATHS_R02','schema':'riverstone.finite_source_index_surface_patch.v1','status':'SOURCE_PATCH_NOT_APPLIED','base_scene_sha256':terrain.SCENE_SHA256,'base_scene':ref(terrain.SCENE_PATH),'source_surface_hashes':{m:terrain.canonical_sha(scene['surfaces'][m])for m in mats},'surface_edits':edits,'appended_surfaces':dict(append),'removed_foundation_proxy_ids':[],'native_pack':ref(packpath),'policy':'Finite actual R7 ground planes only. Existing road/alley, bank, water and native stair faces retained. Ready21 ownership has priority. Use combined patch, not sequential original-index edits, when ready21 is active.'}
 # Preserve all old appended vertices byte-for-byte. On shared source indices,
 # split only old outside triangles by the new disjoint owned regions.
 combined=json.loads(json.dumps(old));combined['id']='R8_CONNECTED_PRECINCT_GROUNDS_AND_EXTENSIONS_R02';combined['native_pack']=ref(packpath);combined['component_native_packs']=[ref(BASE/'resolved_connected_placements.json'),ref(OUT.parent/'resolved_residual_placements.json'),ref(packpath)];combined['component_patches']=[ref(oldpath)];oldmap={(e['material'],e['triangle_index']):e for e in combined['surface_edits']};shared=[]
 for e in edits:
  key=(e['material'],e['triangle_index'])
  if key not in oldmap:combined['surface_edits'].append(e);continue
  ce=oldmap[key];r=by_source[key]['source'];regions=[q['polygon_xz_m']for q in by_source[key]['regions']];replacement=[]
  for tri in ce['replacement_triangles_xyz_m']:
   poly=[[v[0],v[2]]for v in tri]
   for p in terrain.common.subtract([poly],regions):replacement+=terrain.fan_upward(lift(p,r['plane_y_xz_m']))
  ce['replacement_triangles_xyz_m']=replacement;ce['owner_ids']=sorted(set(ce['owner_ids']+e['owner_ids']));shared.append({'material':key[0],'triangle_index':key[1]})
 for mat,vs in append.items():combined['appended_surfaces'].setdefault(mat,[]).extend(vs)
 combined['source_surface_hashes'].update(patch['source_surface_hashes']);combined['policy']='Atomic original-R7 source-index union of sealed ready21 plus new residual fields. Supersedes the ready21 ground patch; do not also apply that patch. Old appended vertices retained verbatim, new ownership disjoint. No bank/water/road/alley edits.'
 checks={'source_scene_hash_matches':sha(terrain.SCENE_PATH)==terrain.SCENE_SHA256,'no_bank_water_or_existing_road_edits':not any(e['material']in('road','alley','bank','water')for e in edits),'all_new_triangles_upward':all(terrain.normal_y(v[i:i+3])>0 for v in append.values()for i in range(0,len(v),3)),'old_appended_vertices_exact_prefix':all(combined['appended_surfaces'][m][:len(v)]==v for m,v in old['appended_surfaces'].items()),'no_duplicate_combined_source_indices':len({(e['material'],e['triangle_index'])for e in combined['surface_edits']})==len(combined['surface_edits']),'finite_conservation':max(p['conservation_error_m2']for p in proof)<1e-6};assert all(checks.values())
 tests={'status':'PASS','checks':checks,'summary':{'residual_source_indices':len(edits),'new_ground_and_walk_area_m2':totalground,'native_cut_area_m2':totalcut,'appended_triangles':sum(len(v)//3 for v in append.values()),'shared_source_indices_merged':len(shared),'combined_source_indices':len(combined['surface_edits']),'maximum_conservation_error_m2':max(p['conservation_error_m2']for p in proof),'seconds':time.monotonic()-t},'shared_source_indices':shared,'retained_public_surfaces_sampled_with_multiplicity_m2':dict(skip),'bank_sha256_unchanged':terrain.canonical_sha(scene['surfaces']['bank']),'water_sha256_unchanged':terrain.canonical_sha(scene['surfaces']['water']),'runtime_ready':False}
 for name,data in [('residual_surface_patch.json',patch),('combined_all_precinct_surface_patch.json',combined),('residual_ground_index_ledger.json',{'per_source':proof}),('residual_ground_tests.json',tests)]: (OUT/name).write_text(json.dumps(data,indent=2)+'\n')
 print(tests['summary'])
if __name__=='__main__':main()
