"""Report net native roof and residual-material priority for the final source set."""
from . import geometry as g
from .activate_backlands_subset import MaskIndex
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from collections import defaultdict
import time
OUT=g.HERE/'final24_source_addendum_r01'
def area(ps):return sum(g.geo.polygon_area(q)for q in ps)
def run():
 start=time.monotonic();pp=OUT/'atomic_source_addendum.json';pack=g.load(pp);projpath=g.CITY/'registered_integration/r8/coverage_plan/native_projection.json';projection={r['id']:r for r in g.load(projpath)['instances']};blocks=defaultdict(lambda:dict(new_holding_ids=[],new_roofs=[],retired_ids=set(),holdings=[]))
 for r in pack['records']:
  bid=r['holding_id'].split(':')[0];b=blocks[bid];b['new_holding_ids'].append(r['holding_id']);b['holdings'].append(r['replacement_holding']['holding_polygon_xz_m']);b['retired_ids'].update(r['replacement_terrain_parcel']['retired_source_ids']);b['new_roofs'] += [q for p in r['replacement_native_placements']if ':FABRIC:'in p['id']for q in p['native_roof_polygons_xz_m']]
 rows=[]
 for bid,b in sorted(blocks.items()):
  new=area(a.common.disjoint_union(b['new_roofs']));old=area(a.common.disjoint_union([q for i in sorted(b['retired_ids'])for q in projection[i]['roof_parts_xz_m']]));owned=area(a.common.disjoint_union(b['holdings']));rows.append(dict(block_id=bid,adopted_holding_ids=b['new_holding_ids'],new_native_roof_union_m2=new,retired_R7_native_roof_union_m2=old,net_roof_union_gain_m2=new-old,logical_holding_union_m2=owned,new_roof_share_of_adopted_holding_land=new/owned,retired_source_ids=sorted(b['retired_ids'])))
 apppath=g.HERE/'backland_completion_r01/residual_material_application_r01/application_handoff.json';app=g.load(apppath);masks=[]
 for r in pack['records']:
  h=r['replacement_holding'];masks += [dict(id=h['id'],kind='FINAL_LOGICAL_HOLDING',polygon_xz_m=h['holding_polygon_xz_m'])]+[dict(id=h['id'],kind='FINAL_ENTRY',polygon_xz_m=q)for q in h['external_route_polygons_xz_m']]
 mi=MaskIndex(masks);contacts=[]
 for k in ['material_application_regions','already_matching_material_regions']:
  for i,r in enumerate(app[k]):
   hits=mi.hit([r['polygon_xz_m']])
   if hits:contacts.append(dict(source_list=k,source_index=i,region_id=r.get('id'),contacts=hits))
 overlap=area(a.common.disjoint_union([x['polygon_xz_m']for r in contacts for x in r['contacts']]));out=dict(schema='riverstone.final23.roof_and_land_source_accounting.v1',native_pack=g.ref(pp),native_roof_source=g.ref(projpath),residual_material_source=g.ref(apppath),blocks=rows,summary=dict(adopted_holdings=len(pack['records']),new_native_roof_union_m2=sum(x['new_native_roof_union_m2']for x in rows),retired_R7_native_roof_union_m2=sum(x['retired_R7_native_roof_union_m2']for x in rows),net_native_roof_union_gain_m2=sum(x['net_roof_union_gain_m2']for x in rows),logical_holding_union_m2=sum(x['logical_holding_union_m2']for x in rows),residual_material_overlap_final_owners_m2=overlap,seconds=time.monotonic()-start),residual_material_owner_contacts=contacts,policy='These are source-bound final-batch incremental native roof unions, not total city roof coverage. Final owner domains take priority over any intersecting residual same-plane material proposal. The B008 hall is retained and its withdrawn546.5m² proposal is not counted as construction.',author=g.ref(__file__));g.write(OUT/'roof_and_land_accounting.json',out);print(out['summary'],flush=True);print(g.ref(OUT/'roof_and_land_accounting.json'),flush=True)
if __name__=='__main__':run()
