"""Finite service circuit recovery overlay, preserving the base reservoir pack."""
import copy,json,math,sys
from author_service import *
from resolve_pack import top_faces,transform_poly
from world_city.concept_city_v3.review_geometry import clean,DomainCut

def main():
 base=json.loads((HERE.parent/'resolved_placements.json').read_text());report=json.loads((HERE/'compile_report.json').read_text());source=json.loads((ROOT/report['source']['path']).read_text());cache=json.loads((ROOT/report['cache']['path']).read_text());pos=[ORIGIN[0],18,ORIGIN[2]];id='RESERVOIR_SERVICE_CIRCUIT_RECOVERY';bounds=cache['bounds'];key=source['id'];asset={k:report[k] for k in ('source','cache','master_hash','pitch_m','candidate_cells','output_cells','quad_count')};asset['id']=key
 p={'id':id,'asset_key':key,'source_id':key,'position_m':pos,'position_xyz_m':pos,'yaw_rad':0,'yaw_degrees':0,'scale':[1,1,1],'scale_xyz':[1,1,1],'actual_cached_bounds_local_m':bounds,'source':report['source'],'cache':report['cache'],'master_hash':report['master_hash'],'network_role':'dry_service_walk_with_two_elevated_crossings'}
 wet=water.finite_water_polygons();cutter=DomainCut(wet);floors=[];decks=[];roadpolys=[]
 for r in DATA['roads']:
  if r['id']in ('RESERVOIR_SERVICE','NORTH_WATERKEEPER'):
   roadpolys += [geo.road_ribbon(a,b,r['width_m']) for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:])]
 native=[]
 for i,q in enumerate(top_faces(cache,0)):
  poly=transform_poly(q,pos,0);native.append(poly)
  for j,part in enumerate(cutter.subtract(poly)):
   floors.append({'id':f'{id}:dry:{i}:{j}','placement_id':id,'polygon_xz_m':part,'floor_y_m':18,'support_bottom_y_m':17.6,'footprint_basis':'Actual upward native quad, clipped to finite dry domain.','priority':'Public travel lane remains primary. Retain wet surface and bed beneath the two elevated crossings.'})
  for j,w in enumerate(wet):
   part=clean(geo.convex_intersection(poly,w['polygon_xz_m']))
   if part:decks.append({'id':f'{id}:wet:{i}:{j}','placement_id':id,'polygon_xz_m':part,'deck_y_m':18,'underside_y_m':17.6,'surface_id':w.get('surface_id',w.get('id')),'water_and_bed_retained':True})
 roadarea=sum(geo.intersection_area(f['polygon_xz_m'],r)for f in floors for r in roadpolys);basearea=sum(geo.intersection_area(f['polygon_xz_m'],r['polygon_xz_m'])for f in floors for r in base['owned_floors']);assert roadarea<1e-7 and basearea<1e-7,(roadarea,basearea)
 pack=copy.deepcopy(base);pack.update(schema='riverstone.city.registered_reservoir_service_recovery.v1',status='compiled_resolved_recovery_candidate_pending_independent_access_and_support',base_pack=ref(HERE.parent/'resolved_placements.json'),recovery_author=ref(Path(__file__)),compile_report=ref(HERE/'compile_report.json'),public_access_handoff=ref(HERE.parent/'public_access_handoff.json'));pack['assets'].append(asset);pack['placements'].append(p);pack['owned_floors']+=floors;pack['elevated_wet_decks']=decks;pack['service_native_floor_regions_xz_m']=native;pack['service_crossings']=BRIDGES;pack['checks']['service_floor_road_overlap_m2']=roadarea;pack['checks']['service_floor_base_apron_overlap_m2']=basearea;pack['checks']['service_6_connected_cells']=report['disconnected_cells']==0;pack['completion_claims'].update(actual_scene_loaded=False,actual_visual_review=False);pack['missing']=['Recovered circuit still needs independent full-width service access and support audit.','Short road handoff remains a separate terrain r10 profile and is not included as a duplicate native face.','Feeder service access, cleaning and drain-down provisions remain unresolved.','Full hydraulic capacity, source yield, potable quality, flood/backwater and mechanical operation remain unvalidated.'];write(HERE/'resolved_placements.json',pack);write(HERE/'recovery_addendum.json',{'schema':'riverstone.city.reservoir_service_recovery_addendum.v1','base_pack':ref(HERE.parent/'resolved_placements.json'),'recovered_pack':ref(HERE/'resolved_placements.json'),'lost_previous_sha256':'916e253a5a1a2dcf0e60fc6c15702efa3440139b4aad35bf8947ad383e9c9bc3','byte_identical_restoration':False,'new_source_revision':key,'public_handoff_unchanged':ref(HERE.parent/'public_access_handoff.json'),'service_floor_pieces':len(floors),'dry_floor_area_m2':sum(geo.polygon_area(x['polygon_xz_m'])for x in floors),'wet_deck_area_m2':sum(geo.polygon_area(x['polygon_xz_m'])for x in decks),'new_asset_count':1,'new_placement_count':1,'actual_placed':False,'actual_viewed':False,'known_r3_exclusion':True});print(json.dumps({'pack':ref(HERE/'resolved_placements.json'),'dry_area':sum(geo.polygon_area(x['polygon_xz_m'])for x in floors),'wet_area':sum(geo.polygon_area(x['polygon_xz_m'])for x in decks),'floors':len(floors)},indent=2))
if __name__=='__main__':main()
