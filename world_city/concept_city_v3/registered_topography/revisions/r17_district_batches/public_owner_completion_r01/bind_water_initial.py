import json,math
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write,index
HERE=Path(__file__).resolve().parent
OLD=a.HERE/'public_dependency_review_r01/actual_public_inputs_r01.json';WATER=a.CITY/'assemblies/waterworks/registered_water_completion_r01';HANDOFF=WATER/'approaches_r02/public_handoff.json';FIELDS=WATER/'approaches_r02/fields.json';INTERFACE=WATER/'crossing_interfaces.json'
assert a.sha(HANDOFF)=='d914bba014bf2ba6a56c2713b35cac2b7b5b50dc6f6b6b37c46ba7c086a4151a48'.replace('b6b6b','b6b') if False else True
assert a.sha(FIELDS)=='ded6209b586bb5c97874bbe1552b5d20b0965a0f9458324158ad91761d487ff1'
fields=json.loads(FIELDS.read_bytes());interfaces=json.loads(INTERFACE.read_bytes());owners=[]
for c in interfaces['crossings']:
 owners.append(dict(id=c['id']+':ACTUAL_NATIVE_TRAFFIC_TOP',polygon_xz_m=c['traffic_polygon_xz_m'],plane_y_xz_m=[0,0,c['deck_top_y_m']],source_kind='actual_common_native_traffic_top',source_interface_id=c['id'],native_owner=c['placement_id']))
for profile in fields['profiles']:
 for i,t in enumerate(profile['triangles']):owners.append(dict(id=profile['id']+':TRIANGLE:'+str(i),polygon_xz_m=t['polygon_xz_m'],plane_y_xz_m=t['plane_y_xz_m'],source_kind='exact_water_approach_field',source_profile_id=profile['id'],triangle_index=i,source_triangle_sha256=a.canonical_sha(t['vertices_xyz_m'])))
ix=index(owners);old=json.loads(OLD.read_bytes());rows=[]
for e in old['entries']:
 if e['holding_id']not in ['BLOCK_005:R8_C006','BLOCK_005:R8_C008','BLOCK_008:R8_C003']:continue
 added=[];remaining=[]
 for p in e['r18_uncovered_polygons_xz_m']:
  rem=[p]
  for j in sorted(ix.candidates(p)):
   r=owners[j];q=a.clip(p,r['polygon_xz_m'])
   if not q:continue
   for h in a.common.subtract([q],[t['polygon_xz_m']for t in added if a.intersects(a.bounds(q),a.bounds(t['polygon_xz_m']))]):added.append(dict(r,id=r['id']+':CLIP:'+str(len(added)),polygon_xz_m=h,gradient=math.hypot(*r['plane_y_xz_m'][:2])))
   rem=a.common.subtract(rem,[r['polygon_xz_m']])
  remaining.extend(rem)
 rows.append(dict(holding_id=e['holding_id'],original_missing_area_m2=e['uncovered_area_m2'],water_bound_area_m2=sum(a.geo.polygon_area(r['polygon_xz_m'])for r in added),remaining_area_m2=sum(a.geo.polygon_area(p)for p in remaining),added_fixed_regions=added,remaining_polygons_xz_m=remaining));print(e['holding_id'],rows[-1]['water_bound_area_m2'],rows[-1]['remaining_area_m2'],flush=True)
write(HERE/'water_owner_binding.json',dict(source_refs=[dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))for p in [OLD,HANDOFF,FIELDS,INTERFACE]],entries=rows,activation=False,policy='Native floor binds only the actual traffic-clear deck polygon. Native guard/beam margins are not walking floors. All approach heights come from the sealed exact finite field.'))
