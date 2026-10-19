"""Independent exact-cache/native metadata audit for the final atomic source set."""
from . import geometry as g
from .rebind_final_district_sources import OUT,ACTUAL,ACTUAL_SHA
from .activate_backlands_subset import ActualNative,MaskIndex
from .rebind_coherent_datums import require
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles,transform
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
import math,time,hashlib,json

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def run():
 start=time.monotonic();path=OUT/'atomic_source_addendum.json';pack=g.load(path);assert g.ref(ACTUAL)['sha256']==ACTUAL_SHA;scene=g.load(ACTUAL);ret=set(pack['retired_source_ids']);sc=dict(scene);sc['common_instances']=[p for p in scene['common_instances']if p['id']not in ret];sc['boxes']=[p for p in scene['boxes']if p['id']not in{i+':owned_foundation'for i in ret}];native=ActualNative(sc);cache={};local={};assets=pack['assets'];bottoms=[];contacts=[];byid={p['id']:p for p in pack['placements']};doors=[]
 for k,ass in assets.items():
  p=g.ROOT/ass['render_path'];assert g.ref(p)['sha256']==ass['render_sha256'];cache[k]=g.load(p);bb=cache[k]['bounds'];local[k]=slab_rectangles(cache[k],bb['min'][1]+.001,bb['max'][1]-.001)
 for p in pack['placements']:
  bb=cache[p['asset_key']]['bounds'];bottom=bb['min'][1]+p['position_m'][1];bottoms.append(dict(id=p['id'],cache_bottom_y_m=bottom,declared_bottom_y_m=p['native_bottom_y_m'],passes=abs(bottom-p['native_bottom_y_m'])<1e-9));polys=[transform(q,p)for q in local[p['asset_key']]];hits=native.hit(polys,bottom+1e-5,p['position_m'][1]+bb['max'][1]-1e-5)
  if hits:contacts.append(dict(id=p['id'],holding_id=p['holding_id'],contacts=hits))
 for d in pack['actual_doors']:
  p=byid[d['parcel_id']];v=d['actual_local_xyz_m'];cc=math.cos(p['yaw_rad']);ss=math.sin(p['yaw_rad']);actual=[p['position_m'][0]+cc*v[0]+ss*v[2],p['position_m'][1]+v[1],p['position_m'][2]-ss*v[0]+cc*v[2]];err=math.dist(actual,d['actual_door_xyz_m']);doors.append(dict(id=d['id'],native_placement_id=p['id'],cache_transform_error_m=err,passes=err<1e-8))
 new_native=[]
 for p in pack['placements']:
  if ':FABRIC:'not in p['id']:continue
  bb=cache[p['asset_key']]['bounds'];new_native.append(dict(p=p,polys=[transform(q,p)for q in local[p['asset_key']]],bottom=p['position_m'][1]+bb['min'][1],top=p['position_m'][1]+bb['max'][1]))
 pairs=[]
 for i,x in enumerate(new_native):
  for y in new_native[i+1:]:
   if min(x['top'],y['top'])-max(x['bottom'],y['bottom'])<=1e-8:continue
   overlap=sum(g.geo.intersection_area(p,q)for p in x['polys']for q in y['polys'])
   if overlap>1e-7:pairs.append(dict(first=x['p']['id'],second=y['p']['id'],projected_solid_overlap_m2=overlap))
 extension_checks=[];extension_contacts=[]
 sc_ext=dict(sc);sc_ext['common_assets']=dict(sc['common_assets'],**assets);sc_ext['common_instances']=sc['common_instances']+pack['placements'];ext_native=ActualNative(sc_ext)
 for ref in pack['profile_native_extensions']:
  ext=require(ref);assert all(ext['checks'].values())
  for p in ext['placements']:
   ass=ext['assets'][p['asset_key']];cp=g.ROOT/ass['render_path'];assert g.ref(cp)['sha256']==ass['render_sha256'];cc=g.load(cp);bb=cc['bounds'];low=bb['min'][1]+p['position_m'][1];high=bb['max'][1]+p['position_m'][1];polys=[transform(q,p)for q in slab_rectangles(cc,bb['min'][1]+1e-5,bb['max'][1]-1e-5)];coarse=ext_native.hit(polys,low+1e-5,high-1e-5);hits=[]
   if coarse:
    cuts=sorted(set([low,high]+[low+i*.125 for i in range(1,math.ceil((high-low)/.125))]))
    for lo,hi in zip(cuts,cuts[1:]):
     pp=[transform(q,p)for q in slab_rectangles(cc,lo-p['position_m'][1]+1e-6,hi-p['position_m'][1]-1e-6)];hh=ext_native.hit(pp,lo+1e-6,hi-1e-6)
     if hh:hits.append(dict(low_y_m=lo,high_y_m=hi,contacts=hh))
   if hits:extension_contacts.append(dict(id=p['id'],exact_slab_contacts=hits))
   extension_checks.append(dict(id=p['id'],all_cache_and_source_checks_pass=True,unit_scale=p['scale']==[1,1,1],variable_bottom_section_count=len(ext['native_bottom_sections']),actual_native_contacts=len(hits),passes=not hits and p['scale']==[1,1,1]))
 payload={k:pack[k]for k in ['records','assets','placements','actual_doors','door_routes','native_earth_bearings','retirement_records','profile_bindings','profile_native_extensions','inner_entry_routes','superseded_domain_handoffs']}
 checks=dict(all_profile_native_extensions_clear_and_bound=all(r['passes']for r in extension_checks),all_inner_entry_chains_source_bound=require(pack['inner_entry_handoff'])['passed'],all_superseded_domains_accounted=all(require(r)['passed']for r in pack['superseded_domain_handoffs']),all_cache_bytes_match=True,all_record_checks=all(r['passed']for r in pack['records']),all_cache_bottoms_match=all(r['passes']for r in bottoms),all_actual_doors_match_cache_transform=all(r['passes']for r in doors),all_unit_scales=all(p['scale']==[1,1,1]for p in pack['placements']),no_retained_native_projection_contacts=not contacts,no_new_range_projection_contacts=not pairs,all_selected_profiles_hash_bound=all(require(r) is not None for r in pack['profile_bindings'].values()))
 report=dict(schema='riverstone.final24.exact_native_source_audit.v1',request=pack['request'],actual_scene=g.ref(ACTUAL),source_payload_sha256=digest(payload),payload_keys=list(payload),checks=checks,passed=all(checks.values()),profile_native_extension_checks=extension_checks,profile_native_extension_contacts=extension_contacts,cache_bottoms=bottoms,actual_door_transforms=doors,retained_native_contact_candidates=contacts,new_range_contact_candidates=pairs,hypothetically_retired_source_ids=sorted(ret),seconds=time.monotonic()-start,author=g.ref(__file__),limits=['Whole-height projected native masks are a conservative screen. Any positive contact remains held pending exact vertical solid review.','The original 61 scene is read-only; all listed old body retirements are hypothetical until the matched final terrain release.','Actual bearing bottoms, retained bank sides, selected finite entry gradients and controller replay are separate R17/integration gates.'])
 g.write(OUT/'native_source_audit.json',report);pack['native_audit']=g.ref(OUT/'native_source_audit.json');pack['status']='ATOMIC_SOURCE_READY_FOR_R17_COMPOSITION'if report['passed']else'HELD_EXACT_NATIVE_CONTACT_OR_TRANSFORM_REVIEW';pack['summary'].update(native_audit_passed=report['passed'],retained_native_contact_candidates=len(contacts),new_range_contact_candidates=len(pairs));g.write(path,pack);print(checks,flush=True);print(g.ref(path),flush=True)
if __name__=='__main__':run()
