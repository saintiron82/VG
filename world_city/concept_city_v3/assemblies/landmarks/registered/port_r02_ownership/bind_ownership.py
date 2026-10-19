"""Prove same-level finite co-ownership, without changing native port solids."""
import copy,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REGISTERED=HERE.parent
sys.path.insert(0,str(REGISTERED))
from build_audit import ROOT,ref,write
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import clean
from world_city.concept_city_v3.registered_topography.revisions.r04_assembly_ownership import port_tie

def main():
 base=REGISTERED/'port_r01';p=base/'resolved_placements.json';pack=json.loads(p.read_text());floor=next(x for x in pack['owned_floors'] if x['id']=='PORT_QUAY_3_8:floor');contract_path=port_tie.HERE/'port_tie_contract.json';contract=json.loads(contract_path.read_text());pieces=[];raw=[]
 for i,poly in enumerate(contract['owned_polygons_xz_m']):
  q=clean(geo.convex_intersection(floor['polygon_xz_m'],poly))
  if q:raw.append({'id':f'PORT_QUAY_3_8:TIE_SHARED:{i}','polygon_xz_m':q})
 for i,poly in enumerate(contract['profile_piece_polygons_xz_m']):
  q=clean(geo.convex_intersection(floor['polygon_xz_m'],poly))
  if q:
   ys=[port_tie.height_at(*point) for point in q]
   assert all(abs(y-2.2)<1e-9 for y in ys),ys
   pieces.append({'id':f'PORT_QUAY_3_8:TIE_SHARED_PROFILE:{i}','polygon_xz_m':q,'vertex_height_m':ys,'floor_y_m':2.2,'max_abs_level_delta_m':max(abs(y-2.2) for y in ys)})
 rawarea=sum(geo.polygon_area(x['polygon_xz_m']) for x in raw);splitarea=sum(geo.polygon_area(x['polygon_xz_m']) for x in pieces)
 assert abs(rawarea-splitarea)<1e-6,(rawarea,splitarea)
 bridge=ROOT/'world_city/concept_city_v3/assemblies/waterworks/registered_bridge'
 value={'schema':'riverstone.city.port_finite_coownership_addendum.v1','status':'full_field_proven_same_level_source_preserved','source_plan':pack['source_plan'],'port_pack':ref(p),'port_integration_base':ref(base/'integration_overlay.json'),'terrain_tie_contract':ref(contract_path),'terrain_tie_author':ref(Path(port_tie.__file__)),'compiled_bridge_pack':ref(bridge/'resolved_placements.json'),'derived_bridge_overlay':ref(bridge/'continuous_deck_overlay.json'),'base_bridge_overlay_sha256':contract['bridge_overlay_sha256'],'provenance_policy':'Frozen tie contract uses the immutable base bridge field. Derived bridge overlay embeds the same tie uplift; do not rewrite the base hash to create a circular provenance.','placement_id':'PORT_QUAY_3_8','source_and_cache_unchanged':next(x for x in pack['placements'] if x['id']=='PORT_QUAY_3_8'),'shared_regions':raw,'proof_regions':pieces,'proof':{'method':'Intersect exact apron with tie domains already split at every bridge profile breakplane. On each convex piece the bridge height is linear, tie height is max(2.2, that field), so all vertices at2.2 prove all interior points at2.2.','raw_intersection_pieces':len(raw),'profile_split_pieces':len(pieces),'raw_area_m2':rawarea,'profile_split_area_m2':splitarea,'coverage_error_m2':abs(rawarea-splitarea),'all_vertex_values_m':2.2,'whole_field_flat':True},'ownership_rule':{'visible_solid_and_top_owner':'PORT_QUAY_3_8 common source/cache','traversal_semantics_owner':'PORT_BRIDGE_TIE','suppress_duplicate_terrain_or_road_top_only_inside_shared_regions':True,'road_xz_or_width_changes':False,'road_height_changes':False,'common_asset_edits':False,'rising_tie_outside_shared_regions':'Retain exact terrain r04 height field and bridge junction uplift.','river_water_bed_changes':False},'actual_scene_applied':False,'actual_visual_review':False}
 write(HERE/'finite_coownership_addendum.json',value)
 overlay=copy.deepcopy(json.loads((base/'integration_overlay.json').read_text()));overlay['source_pack']=ref(p);overlay['base_overlay']=ref(base/'integration_overlay.json');overlay['continuous_bridge_overlay']=value['derived_bridge_overlay'];overlay['finite_port_tie_ownership']=ref(HERE/'finite_coownership_addendum.json');overlay['single_top_surface_rules'][1]={'placement_ids':['PORT_QUAY_3_8'],'road_id':'PORT_BRIDGE_TIE','status':'full_field_proven_flat_common_apron_coownership','finite_regions':ref(HERE/'finite_coownership_addendum.json'),'traffic_semantics_owner':'PORT_BRIDGE_TIE','common_visible_top_owner':'PORT_QUAY_3_8','height_m':2.2,'requirement':'Suppress only duplicate tie top triangles inside exact shared_regions. Preserve the common apron and its solid. Retain rising tie profile and bridge opening outside those finite pieces.'};write(HERE/'integration_overlay.json',overlay)
 print(json.dumps(value['proof'],indent=2))
if __name__=='__main__':main()
