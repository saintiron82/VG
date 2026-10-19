"""Image-guided outside woodland, using the existing irregular common recipes.
No tree scaling, new compiler, indoor city forest, or added floor surfaces.
"""
import hashlib,json,math,copy
from pathlib import Path
from world_city.concept_city_v3.assemblies.landscape import recipes
from world_city.concept_city_v3.assemblies.landscape.resolve_approved import project
from world_city.concept_city_v3.registered_topography import author as terrain
from world_city.runtime_city.checks import placement as geo
HERE=Path(__file__).parent;ROOT=HERE.parents[4];CITY=HERE.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,o):p.write_text(json.dumps(o,indent=2)+'\n')
def bbox(p):return [min(x[0] for x in p),min(x[1] for x in p),max(x[0] for x in p),max(x[1] for x in p)]
def touches(a,b):return a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]
def main():
 planpath=CITY/'registered_source/plan.json';plan=json.loads(planpath.read_text());wall=plan['boundary_xz_m'];source_sha=sha(planpath)
 # Shared wall edges are source-derived. Outer extent is an authored forest
 # reservation inferred from the painting, not an observed survey boundary.
 north=[[-530,-530],[110,-530],[110,-420],wall[6]]+list(reversed(wall[:6]))+[[-530,wall[0][1]]]
 west=[[-530,wall[0][1]],[-440,wall[0][1]],[-440,wall[22][1]],[-530,wall[22][1]]] # conservative finite exterior stand; wall-side residual stays unassigned meadow
 sites=[dict(id='WOOD_REGISTERED_NORTHWEST',landscape_kind='outside_woodland',polygon_xz_m=north,maximum_trees=550,seed=145001),dict(id='WOOD_REGISTERED_WEST',landscape_kind='outside_woodland',polygon_xz_m=west,maximum_trees=350,seed=145002)]
 ex=[]
 for r in plan['roads']:
  for i,(a,b) in enumerate(zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])):ex.append(dict(id=r['id']+':'+str(i),polygon_xz_m=geo.road_ribbon(a,b,r['width_m']+8)))
 for d in terrain.finite_water_polygons():ex.append(dict(id='WET:'+d['surface_id'],polygon_xz_m=d['polygon_xz_m']))
 for w in terrain.WATERS:
  for i,(a,b) in enumerate(zip(w['polyline_xz_m'],w['polyline_xz_m'][1:])):ex.append(dict(id='WATER_BANK:'+w['id']+':'+str(i),polygon_xz_m=geo.road_ribbon(a,b,w['width_m']+8)))
 existing=json.loads((HERE.parent/'resolved_placements.json').read_text())['asset_manifest'];assets={};placed=[];rejected=[];records=[]
 for site in sites:
  pb=bbox(site['polygon_xz_m']);local=[e for e in ex if touches(pb,bbox(e['polygon_xz_m']))]
  recipe=recipes.build_landscape_recipe(site,wall,local);write(HERE/(site['id']+'.recipe.json'),recipe)
  if not recipe['checks']['valid']:raise ValueError(recipe['checks'])
  count=0
  for p in recipe['placements']:
   key=p['asset_key'];a=existing[key]
   for kind,hashkey in [('render','render_sha256'),('master','master_file_sha256')]:
    path=Path(a[kind+'_path']);path=path if path.is_absolute() else ROOT/path
    assert sha(path)==a[hashkey]
   q,error=project(p,terrain.land_height_at)
   if error:rejected.append(error);continue
   q['palette_id']='native_woodland';q['palette_override']={};q['source_plan_sha256']=source_sha;q['scale']=[1,1,1]
   for kind in ('render','master'):
    path=Path(a[kind+'_path']);path=path if path.is_absolute() else ROOT/path
    a[kind+'_path']=str(path.relative_to(ROOT))
   assets[key]=copy.deepcopy(a);placed.append(q);count+=1
  records.append(dict(site=site,recipe_checks=recipe['checks'],recipe_metrics=recipe['metrics'],placed_count=count,clearings=recipe['clearings'],no_new_ground_plane=True))
  print(json.dumps({'site':site['id'],'placed':count,'metrics':recipe['metrics']}),flush=True)
 result=dict(schema='riverstone.registered_woodland.v1',status='native_cached_placement_candidate_pending_visual_review',source_plan_sha256=source_sha,terrain_author_sha256=sha(terrain.__file__),source_controls_sha256=plan['registration']['controls_sha256'] if 'controls_sha256' in plan['registration'] else None,sites=records,placements=placed,assets=assets,rejections=rejected,summary=dict(instances=len(placed),trees=sum(p['spec']['kind']=='forest_tree' for p in placed),understory=sum(p['spec']['kind']=='understory' for p in placed),unique_assets=len(assets),new_compiles=0,scaled_trees=0,new_floor_surfaces=0),limits=['Forest edge extent is inferred from image and corrected wall; exact tree locations are deterministic authored clusters.','Existing rounded common crowns, root-only collision policy; no blanket canopy collider.','No urban estate or monastery garden ownership is taken by this pack.'])
 assert sha(planpath)==source_sha
 write(HERE/'resolved_placements.json',result);write(HERE/'summary.json',result['summary']);print(result['summary'])
if __name__=='__main__':main()
