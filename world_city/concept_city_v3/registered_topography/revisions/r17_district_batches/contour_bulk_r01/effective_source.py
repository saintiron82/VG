"""Immutable derived 14-district input with the one explicit dry-side repair."""
import json,copy
from .screen import HERE,write
from .. import author as a,native_clearance
ADDENDUM=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/contour_revision_r01/b05_dryside_addendum_r01.json'
ADDENDUM_SHA='4c5eaf69d7035217142f3852f5f58b98f52810067c3c7fe41dab6b83a3263c22'

def run():
 assert a.sha(ADDENDUM)==ADDENDUM_SHA
 add=json.loads(ADDENDUM.read_bytes());source_folders=[HERE,a.HERE/'remaining_level_r01'];ls=[json.loads((p/'combined_source_layout.json').read_bytes())for p in source_folders];prepared=[json.loads((p/'prepared_ownership.json').read_bytes())for p in source_folders]
 layout={k:[r for l in ls for r in l[k]]for k in('placements','holdings','actual_doors','retirement_records','shared_private_routes')};layout['retired_source_ids']=sorted({x for l in ls for x in l['retired_source_ids']});layout.update(base_scene_sha256=a.SCENE_SHA256,source_references=[dict(path=str((p/'combined_source_layout.json').relative_to(a.ROOT)),sha256=a.sha(p/'combined_source_layout.json'))for p in source_folders]+[dict(path=str(ADDENDUM.relative_to(a.ROOT)),sha256=ADDENDUM_SHA)],activation=False)
 assets={}
 for l in ls:
  for key,value in native_clearance.require_ref(l['native_local'])['assets'].items():
   if key in assets and a.canonical_sha(value)!=a.canonical_sha(assets[key]):raise ValueError('Conflicting native '+key)
   assets[key]=value
 write('effective_native_local.json',dict(assets=assets,source_references=[l['native_local']for l in ls]));layout['native_local']=dict(path=str((HERE/'effective_native_local.json').relative_to(a.ROOT)),sha256=a.sha(HERE/'effective_native_local.json'))
 h=next(h for h in layout['holdings']if h['id']==add['holding_id']);old=add['superseded_route'];new=add['replacement_route'];assert h['external_route']==old['polyline_xz_m'];assert h['external_route_polygons_xz_m']==old['polygons_xz_m'];h['external_route']=new['polyline_xz_m'];h['external_route_polygons_xz_m']=new['polygons_xz_m'];h['public_target_xz_m']=new['polyline_xz_m'][-1];h['source_route_supersession']=dict(path=str(ADDENDUM.relative_to(a.ROOT)),sha256=ADDENDUM_SHA)
 parcels=[p for d in prepared for p in d['parcels']];parcel=next(p for p in parcels if p['id']==add['holding_id']);oldhashes={a.canonical_sha(p)for p in old['polygons_xz_m']};retained=[p for p in parcel['walk_polygons_xz_m']if a.canonical_sha(p)not in oldhashes];parcel['walk_polygons_xz_m']=retained+new['polygons_xz_m'];parcel['source_route_supersession']=h['source_route_supersession']
 scene=a.load_scene();water=[r['polygon_xz_m']for r in scene['terrain_contract']['water_domain_polygons']];wi=a.geo._SpatialIndex(16)
 for i,p in enumerate(water):wi.add(i,p)
 wet=[]
 for p in parcel['walk_polygons_xz_m']:
  for i in wi.candidates(p):
   q=a.clip(p,water[i])
   if q and a.geo.polygon_area(q)>1e-7:wet.append(dict(water_index=i,polygon_xz_m=q))
 if wet:raise ValueError('Dry-side repair still intersects water')
 write('effective_source_layout.json',layout);write('effective_prepared_parcels.json',dict(parcels=parcels,retirement_records=[r for d in prepared for r in d['retirement_records']],native_earth_bearings=[r for d in prepared for r in d['native_earth_bearings']],source_references=layout['source_references'],dryside_review=dict(holding_id=h['id'],remaining_wet_conflicts=wet,public_target_xz_m=h['public_target_xz_m']),activation=False));print(dict(holdings=len(layout['holdings']),ranges=len(layout['placements']),actual_doors=len(layout['actual_doors']),retired_ids=len(layout['retired_source_ids']),dryside_water_conflicts=len(wet)))
if __name__=='__main__':run()
