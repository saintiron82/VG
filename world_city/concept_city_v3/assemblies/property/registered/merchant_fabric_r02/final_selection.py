"""Post-cache finite-owner filter; compiled building recipes remain unchanged."""
import copy,json
from pathlib import Path
from collections import Counter
from .grammar import HERE,ROOT,CITY,ref,write,g,estate
from world_city.concept_city_v3.registered_source.author import Domain

def additional_owners():
 domain=Domain();sources=[]
 for path in (CITY/'assemblies/property/registered/r1/repair_01/resolved_placements.json',CITY/'assemblies/landscape/registered/resolved_placements.json'):
  s=json.loads(path.read_text());sources.append(ref(path))
  for m in s['ownership_masks']:
   identity=m.get('owner_id',m.get('id'))
   polys=m.get('terrain_exclusion_regions_xz_m',[])+m.get('logical_owned_floor_regions_xz_m',[])+m.get('external_access_domains_xz_m',[])
   if m.get('polygon_xz_m'):polys+=[m['polygon_xz_m']]
   for q in polys:
    for tri in ([q] if g.is_convex_polygon(q) else estate.triangulate(q)):domain.add(tri,identity)
 return domain,sources

def run():
 s=json.loads((HERE/'eligibility.json').read_text());domain,refs=additional_owners();checks=[];kept=[];rejected=[]
 for p in s['properties']:
  hits=[]
  for kind,poly in [('platform',p['polygon_xz_m']),('gate',p['external_gate_link']['polygon_xz_m'])]:
   for i in domain.index.candidates(poly):
    q=domain.polys[i]
    if g.positive_area_overlap(poly,q,1e-7):hits.append(dict(kind=kind,owner_id=domain.ids[i],intersection_polygon_xz_m=g.convex_intersection(poly,q)))
  checks.append(dict(property_id=p['id'],conflicts=hits))
  if hits:rejected.append(p['id'])
  else:kept.append(p)
 out=copy.deepcopy(s);out['base_eligibility']=ref(HERE/'eligibility.json');out['additional_native_owner_sources']=refs;out['final_filter']=ref(Path(__file__));out['status']='effective_source_selection_after_exact_estate_and_landscape_owner_filter';out['properties']=kept;out['rejected_by_exact_native_owner']=rejected;out['replacement_ledger']=dict(replaced_placement_ids=sorted({v for p in kept for v in p['source_retired_native_ids']}),superseded_source_path_ids=sorted({v for p in kept for v in p['superseded_source_path_ids']}),superseded_native_access_ids=sorted({v for p in kept for v in p['superseded_native_access_ids']}));out['summary'].update(properties=len(kept),blocks=dict(Counter(p['block_id'] for p in kept)),families=dict(Counter(p['family'] for p in kept)),retired_native_ids=len(out['replacement_ledger']['replaced_placement_ids']),native_modules=sum(len(p['placements']) for p in kept),actual_doors=sum(len(p['actual_doors']) for p in kept),owned_platform_area_m2=sum(p['width_m']*p['depth_m'] for p in kept),service_court_area_m2=sum(p['court']['area_m2'] for p in kept),native_body_gain_m2=sum(p['body_gain_m2'] for p in kept),continuous_native_street_front_m=sum(p['native_street_frontage_m'] for p in kept));write(HERE/'effective_eligibility.json',out);write(HERE/'exact_owner_filter.json',dict(base=ref(HERE/'eligibility.json'),effective=ref(HERE/'effective_eligibility.json'),sources=refs,checks=checks,rejected_ids=rejected,status='pass_after_explicit_removal',note='The northern candidate intersects E6 real common boundary geometry; a wall-top sample is not eligible terrain. Its source recipe/cache is retained, but its placement and retirements are omitted.'));print(json.dumps(out['summary'],indent=2));return out
if __name__=='__main__':run()
