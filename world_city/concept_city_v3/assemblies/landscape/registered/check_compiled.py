"""Read-only persisted-cache checks; no controller or complete support claim."""
import json,sys
from pathlib import Path
from . import context as c
from world_city.concept_city_v3.assemblies.property.registered import author as a
sys.path.insert(0,str(c.CITY/'validation'))
from check_landmark_access_candidate import slab_rectangles,transform
from check_registered_source import spatial
import geometry as g

def run():
 path=c.HERE/'resolved_placements.json';pack=json.loads(path.read_text());slabs={};renders={};issues=[];hashes=[];obstacles=[];routes=[]
 for key,asset in pack['asset_manifest'].items():
  for f,h in (('master_path','master_file_sha256'),('compiled_asset_ref','render_sha256')):
   actual=a.file_sha(asset[f]);assert actual==asset[h];hashes.append(dict(asset_key=key,kind=f,sha256=actual))
  renders[key]=json.loads(Path(asset['compiled_asset_ref']).read_text());slabs[key]=slab_rectangles(renders[key],.05,1.85)
 for p in pack['placements']:
  for j,poly in enumerate(slabs[p['asset_key']]):obstacles.append(dict(id=p['id']+':slab:'+str(j),owner_id=p['id'],poly=transform(poly,p)))
 query=spatial(obstacles)
 for site in pack['sites']:
  routes.extend(site['internal_paths']);con=site['external_connection']
  if 'ribbon_polygons_xz_m' in con:routes.append(con)
 for r in routes:
  for j,poly in enumerate(r['ribbon_polygons_xz_m']):
   for o in query(poly):
    ar=g.area(g.convex_intersection(poly,o['poly']))
    if ar>1e-5:issues.append(dict(kind='compiled_slab_ribbon_overlap',route_id=r['id'],segment=j,obstacle_id=o['id'],owner_id=o['owner_id'],polygon_xz_m=o['poly'],area_m2=ar))
 # Every stored terrain mask is tied to its actual persisted asset, rather than a broad source boundary.
 for mask in pack['ownership_masks']:
  p=next(p for p in pack['placements'] if p['id']==mask['owner_id']);assert mask['sampled_render_sha256']==p['render_sha256'];assert mask['terrain_exclusion_regions_xz_m']==[r['polygon_xz_m'] for r in mask['compiled_upward_faces']]
 report=dict(schema='riverstone.registered_landscape.persisted_slab_check.v1',source_pack_sha256=pack['source_pack_sha256'],resolved_pack_sha256=a.file_sha(path),checker_sha256=a.file_sha(__file__),slab_checker_sha256=a.file_sha(c.CITY/'validation/check_landmark_access_candidate.py'),status='fail' if issues else 'pass_bounded_native_ribbon_check',counts=dict(placements=len(pack['placements']),assets=len(pack['asset_manifest']),native_slab_rectangles=len(obstacles),full_width_internal_and_branch_routes=len(routes),issues=len(issues)),hash_checks=hashes,issues=issues,limits=['Closed-mesh 0.05–1.85m local walking-height slab against every declared full ribbon.','No capsule, vehicle, complete floor support or actual 3D review claim.','External park ramp quantization, public interface ownership and native landmark approach grades remain explicit downstream reviews.'])
 (c.HERE/'compiled_checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('status','counts','issues')},indent=2));return report
if __name__=='__main__':raise SystemExit(2 if run()['issues'] else 0)
