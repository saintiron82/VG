"""A bounded width-correct bridge sample; no placement or terrain override."""
from pathlib import Path
import copy,json,sys
ROOT=Path(__file__).resolve().parents[5];sys.path.insert(0,str(ROOT));HERE=Path(__file__).resolve().parent
from voxel_character.common import coordinate_planes,core,render_data
from world_city.concept_city_v3.assemblies.landmarks.author import ref,write,source_bounds
from world_city.concept_city_v3.topography.author import river_water_y,road_height_at,height_at


def build():
 base=HERE.parent/'masters/stone_road_bridge_bay.json';original=json.loads(base.read_text());m=copy.deepcopy(original);m['id']='v3_stone_road_bridge_bay_9m_deck'
 for c in m['components']:
  for op in c['operations']:
   s=op['shape']
   if op['id']=='stone_bay':s['min'][2],s['max'][2]=-4.5,4.5
   elif op['id']=='barrel_opening':s['z_min'],s['z_max']=-4.51,4.51
   elif op['id'].startswith('parapet_'):
    side=1 if s['max'][2]>0 else -1;s['min'][2],s['max'][2]=side*4.3-.2,side*4.3+.2
 for c in m['constraints']:
  if c['id']=='road_deck':c['shape']['min'][2],c['shape']['max'][2]=-4,4
  if c['id']=='center_waterway':c['shape']['min'][2],c['shape']['max'][2]=-4.51,4.51
 e=m['extensions'];e['authored_parameters'].update(deck_total_width_m=9,road_clear_width_m=8,physical_width_between_parapets_m=8.2)
 for c in e['clearances']:
  if c['id']=='road_deck':c['region_m']['min'][2],c['region_m']['max'][2]=-4,4;c['purpose']='8 m road reservation within 8.2 m physical parapet gap.'
  if c['id']=='center_waterway':c['region_m']['min'][2],c['region_m']['max'][2]=-4.51,4.51
 for s in e['supports']:s['contact_region_m']['min'][2],s['contact_region_m']['max'][2]=-4.5,4.5
 e['local_bounds_m']=source_bounds(m);e['footprint_xz_m']=[[-8,-4.5],[8,-4.5],[8,4.5],[-8,4.5]];e['city_placement']=None;e['terrain_placement']=None
 m['provenance']['width_adaptation']={'author':ref(str(Path(__file__).relative_to(ROOT))),'original_source':ref(str(base.relative_to(ROOT))),'method':'Explicit new source deck/barrel/parapet widths and clearance regions; no mesh or whole-object scaling.','target_contract':'Current main bridge total deck width 9 m and road width 8 m. No world placement.'}
 write(HERE/'masters/stone_road_bridge_bay_9m.json',m)
 c=coordinate_planes.compile_master(m,{'pitch':.2},max_candidate_cells=400000,max_output_cells=120000);assert c['valid'];r=render_data.make_render_data(c);write(HERE/'cache/stone_road_bridge_bay_9m.pitch_0.2.render.json',r)
 report={'id':m['id'],'valid':True,'source':ref(str((HERE/'masters/stone_road_bridge_bay_9m.json').relative_to(ROOT))),'render':ref(str((HERE/'cache/stone_road_bridge_bay_9m.pitch_0.2.render.json').relative_to(ROOT))),'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'payload_hash':c['payload_hash'],'constraints':c['constraints'],'actual_placed':False,'visually_reviewed':False,'frozen_base_unchanged':json.loads(base.read_text())==original};write(HERE/'evidence/compile_report.json',report)
 plan=json.loads((ROOT/'world_city/concept_city_v3/source/plan.json').read_text());bridge=next(b for b in plan['bridges'] if b['id']=='BRIDGE_MAIN_RIVER');x=bridge['position_xz_m'][0];water=river_water_y(x);candidate=water+2.08
 samples=[{'xz_m':[x,z],'current_road_y_m':road_height_at(bridge['road_id'],x,z),'earth_or_bed_y_m':height_at(x,z),'current_water_y_m':water,'water_plus_2_08_m':candidate,'difference_m':candidate-road_height_at(bridge['road_id'],x,z)} for z in (398,414,420,430,446,462,465,478,494,510,514,530)]
 discrepancy={'schema':'riverstone.city.bridge_datum_discrepancy.v1','status':'record_only_no_override','source_plan':ref('world_city/concept_city_v3/source/plan.json'),'terrain_author':ref('world_city/concept_city_v3/topography/author.py'),'bridge_id':bridge['id'],'source_plan_stored_water_level_m':bridge['water_level_m'],'current_river_water_y_m':water,'matching_head_plus_2_08_m':candidate,'samples':samples,'finding':'Current cart-deck field is a supported cone/terrain profile, not a constant water+2.08 bridge plane across the full river. Stored plan water_level_m is also stale relative to the current river field.','required_next_decision':'After concept-image/world registration, choose exact bridge deck/profile, source approach ramps, half-pier ownership and bank joins together. No automatic flat deck override has been applied.','actual_world_placements':0,'source_plan_modified':False,'terrain_modified':False}
 write(HERE/'bridge_datum_discrepancy.json',discrepancy)
 print(json.dumps({'bridge_sample_candidates':c['candidate_cells'],'output_cells':len(c['cells']),'current_water':water,'candidate_head_plus_2_08':candidate,'placement_count':0}))
if __name__=='__main__':build()
