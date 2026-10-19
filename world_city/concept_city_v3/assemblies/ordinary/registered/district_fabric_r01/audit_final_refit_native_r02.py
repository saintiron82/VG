"""Independent retained-native screen against the parent's actual 61 scene."""
from . import geometry as g
from .activate_backlands_subset import ActualNative,MaskIndex
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles,transform
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import public_domain
from collections import Counter
import sys,time

def run():
 start=time.monotonic();paths=[g.HERE/p/'source_candidates.json'for p in sys.argv[1:]];rows=[r for p in paths for r in g.load(p)['records']];scene_path=g.CITY/'evidence/r8_district_61_assembly_preflight_r01/scene.json';scene=g.load(scene_path);retire=set()
 lp=g.CITY/'registered_topography/revisions/r17_district_batches/contour_bulk_r01/effective_source_layout_r03.json';layout=g.load(lp)
 # All remaining source retirements are still hypothetical and must be bound
 # atomically by the final district release. No active instance is edited here.
 ledger=g.load(g.CITY/'registered_topography/revisions/r17_district_batches/public_dependency_review_r01/remaining17_and_b07_ledger_r01.json');held={r['holding_id']for r in ledger['held_holdings']}
 for h in layout['holdings']:
  if h['id']in held:retire.update(h['retired_source_ids'])
 bp=g.HERE/'b07_terrace_refit_r02/BLOCK_007/selected_layout.json';b07=g.load(bp)
 for h in b07['holdings']:retire.update(h['retired_source_ids'])
 sc=dict(scene);sc['common_instances']=[p for p in scene['common_instances']if p['id']not in retire];sc['boxes']=[p for p in scene['boxes']if p['id']not in{i+':owned_foundation'for i in retire}];native=ActualNative(sc);pub=MaskIndex([dict(r,kind='CANONICAL_PUBLIC')for r in public_domain.records()]);waters=MaskIndex([dict(id='WATER:'+str(i//3),polygon_xz_m=[[v[0],v[2]]for v in scene['surfaces']['water'][i:i+3]])for i in range(0,len(scene['surfaces']['water']),3)]);cache={};result=[]
 for r in rows:
  n=g.load(g.ROOT/r['native_local']['path'])['assets'];contacts=[]
  for p in r['replacement_native_placements']:
   ass=n[p['asset_key']]['asset'];key=ass['render_sha256']
   if key not in cache:
    path=g.ROOT/ass['render_path'];assert g.ref(path)['sha256']==key;render=g.load(path);bb=render['bounds'];cache[key]=(bb,slab_rectangles(render,bb['min'][1]+.001,bb['max'][1]-.001))
   bb,local=cache[key];polys=[transform(q,p)for q in local];hits=native.hit(polys,p['position_m'][1]+bb['min'][1]+1e-5,p['position_m'][1]+bb['max'][1]-1e-5)
   if hits:contacts.append(dict(id=p['id'],contacts=hits))
  feet=[q for p in r['replacement_native_placements']for q in p['native_foundation_polygons_xz_m']];domain=r['flat_owner_polygons_xz_m']+r['profile_domain_polygons_xz_m'];wet=waters.hit(domain);public_flat=pub.hit(r['flat_owner_polygons_xz_m']);out=dict(holding_id=r['holding_id'],actual_61_native_contacts=contacts,wet_contacts=wet,flat_owner_public_contacts=public_flat,passes=not contacts and not wet and not public_flat);result.append(out);print(r['holding_id'],dict(native=len(contacts),wet=len(wet),public_flat=len(public_flat)),flush=True)
 outdir=g.HERE/'final_refit_retained_review_r02';outdir.mkdir(exist_ok=True);report=dict(schema='riverstone.final_refit.actual61_native_screen.v1',candidate_sources=[g.ref(p)for p in paths],actual_scene=g.ref(scene_path),hypothetically_retired_source_ids=sorted(retire),records=result,passed=all(r['passes']for r in result),seconds=time.monotonic()-start,author=g.ref(__file__),scope='Exact cache projection and height-slab conservative native collision screen. Water and canonical-public ownership checked separately. Final terrain, bearing, profile and boundary acceptance remains R17; any projected collision requires exact vertical review before rejection.');g.write(outdir/'audit.json',report);print(g.ref(outdir/'audit.json'),flush=True)

if __name__=='__main__':run()
