"""Non-mutating cached placement/access overlay plus bounded service annex.

Does not rewrite source plan or frozen landmark masters/caches.
"""
from pathlib import Path
import copy,json,sys
ROOT=Path(__file__).resolve().parents[5];sys.path.insert(0,str(ROOT));HERE=Path(__file__).resolve().parent
from voxel_character.common import coordinate_planes,core,render_data
from world_city.concept_city_v3.assemblies.landmarks.author import ref,write,placement,source_bounds,ROOFS
from world_city.concept_city_v3.assemblies.landmarks.resolve_placements import resolve
from world_city.runtime_city.archetypes.ordinary_r2 import make_master
from world_city.concept_city_v3.topography.author import height_at


def build():
 before={p:p.read_bytes() for p in [ROOT/'world_city/concept_city_v3/source/plan.json',*(HERE.parent/'masters').glob('*.json')]}
 recipe=resolve();assert recipe['support_pass'],'Current terrain does not support frozen landmarks'
 proxy=json.loads((HERE.parent/'proxy_masses.json').read_text());access=json.loads((HERE.parent/'access_supersession_proposal.json').read_text())
 spec={'asset_id':'v3_cathedral_service_lodge','assembly_class':'servant_lodge','style':'institutional','width_m':14,'depth_m':10,'floors':1,'roof_form':'gable','roof_pitch_degrees':38,'construction_era':'early'}
 m=make_master(spec);original_hash=core.digest(m)
 # Host terrace owns the plinth and threshold surface. Source floor/walls remain.
 m['components']=[c for c in m['components'] if c['id']!='foundation'];m['instances']=[i for i in m['instances'] if i['component']!='foundation'];m['constraints']=[c for c in m['constraints'] if c['id']!='foundation_present']
 m['materials'].update({k:v for k,v in ROOFS['slate_gray'].items() if k in m['materials']});m['provenance']['v3_adaptation']={'source_master_hash':original_hash,'author':ref(str(Path(__file__).relative_to(ROOT))),'purpose':'Modest cathedral service lodge; no chapter-house interior or full cloister wing claimed.','changes':['Omit standalone stone foundation/threshold: existing cathedral terrace is the bearing host.','Canonical gray-slate roof role.'],'world_placement':'Separate overlay; source geometry is unscaled.'}
 write(HERE/'masters/cathedral_service_lodge.json',m)
 c=coordinate_planes.compile_master(m,{'pitch':.5},max_candidate_cells=400000,max_output_cells=120000);assert c['valid'];render=render_data.make_render_data(c);write(HERE/'cache/cathedral_service_lodge.pitch_0.5.render.json',render)
 sample={'id':'cathedral_service_lodge','source':ref(str((HERE/'masters/cathedral_service_lodge.json').relative_to(ROOT))),'render':ref(str((HERE/'cache/cathedral_service_lodge.pitch_0.5.render.json').relative_to(ROOT))),'valid':c['valid'],'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'payload_hash':c['payload_hash'],'constraints':c['constraints']}
 additions=[];support=[]
 for id,x in [('cathedral_service_west',300),('cathedral_service_east',324)]:
  z=-277;ground=14;pos=[x,ground-.5,z]
  # Closed source door threshold Y=.5 aligns with the shared +14 m terrace.
  for xx in (x-7,x,x+7):
   for zz in (z-5,z,z+5):support.append({'id':id,'xz_m':[xx,zz],'height_y_m':height_at(xx,zz),'expected_m':ground,'pass':abs(height_at(xx,zz)-ground)<1e-7})
  additions.append({'id':id,'kind':'service_annex','assembly':'cathedral','render':sample['render'],'transform':placement(pos),'datum':'cathedral_bench','source':sample['source'],'door_state':'closed','entrance_world_xyz_m':[x,14,z+4],'source_function':'servant_lodge adapted as clergy/service accommodation','interior_access_status':'not_validated'})
 assert all(s['pass'] for s in support)
 paths=[]
 for p in access['primary_opening_link_proposals']:
  paths.append({'id':p['id'],'kind':'landmark_primary_access','owner_assembly':p['group'],'width_m':p['width_m'],'polyline_xz_m':p['path_xz_m'],'source_openings':p['source_openings'],'height_policy':'assembly bench inside host footprint; continuous current terrain/road support outside; no copied old parent door datum','evidence_status':'independent capsule-eroded source-envelope audit passed; actual common capsule collision not certified'})
 suppressed=sorted({x for g in proxy['groups'] for x in g['suppress_blockout_building_ids']})
 current_plan=json.loads((ROOT/'world_city/concept_city_v3/source/plan.json').read_text())
 # Newer source blockouts also supersede three old port warehouse envelopes.
 group_ids={g['id'] for g in proxy['groups']}
 suppressed=sorted(set(suppressed)|{b['id'] for b in current_plan['buildings'] if b.get('superseded_by_component_group_id') in group_ids})
 pack={'schema':'riverstone.city.cached_assembly_integration_pack.v1','status':'staged_overlay_held_for_concept_image_registration','apply_allowed':False,'registration_gate':'Latest user priority is direct concept-image/world registration. Do not apply these candidate transforms or road/path edits before that review.','source_plan':ref('world_city/concept_city_v3/source/plan.json'),'terrain_author':ref('world_city/concept_city_v3/topography/author.py'),'frozen_manifest':ref(str((HERE.parent/'assemblies.json').relative_to(ROOT))),'placements':recipe['placements']+additions,'suppress_building_ids':suppressed,'suppress_path_ids':[p['id'] for p in access['obsolete_parent_paths']],'replace_road_polylines':[{'id':'R_CASTLE','old_polyline_xz_m':access['road_proposal']['old_polyline_xz_m'],'polyline_xz_m':access['road_proposal']['proposed_polyline_xz_m'],'width_m':7}],'add_paths':paths,'surface_ownership_masks':recipe['surface_ownership_masks'],'support_checks':recipe['support_checks'],'dock_pile_bed_checks':recipe['dock_pile_bed_checks'],'quay_footing_bed_checks':recipe['quay_footing_bed_checks'],'boat_waterline_checks':recipe['boat_waterline_checks'],'annex_support_checks':support,'annex_sample':sample,'support_pass':True,'visibility':{'cathedral_cloister_bays':13,'monastery_cloister_bays':13,'cathedral_service_annexes':2,'port_groups':3,'port_components':'Each main cache has two warehouses, quay, dock, foundations and piles; fine placements add cranes, barges and cargo.'},'source_files_modified':False,'actual_scene_loaded':False,'missing':['Full cathedral chapter-house/interior and closed cloister corners','Runtime crane, gate, boat and service-door dynamics','Actual common mesh/capsule traversal and target-scene visual review','Source surfaces must be suppressed under owned floors; water and bed retained']}
 pack['suppress_component_proxy_group_ids']=sorted(group_ids)
 pack['suppress_path_ids']=sorted({p['id'] for p in current_plan['paths'] if p.get('owner_building_id') in suppressed})
 pack['unresolved_port_access']=[{'assembly':'port_cluster_'+str(x),'warehouse':side,'actual_source_entrance_world_xyz_m':[x+dx,2.2,371],'status':'Source opening known; new exterior connector awaits concept registration and full-width audit. Old parent path must not be reused.'} for x in (-180,0,180) for side,dx in [('west',-21),('east',21)]]
 pack['missing'] += ['Six actual port warehouse approach links remain unapproved; no old parent door link is substituted.','Two service annexes have closed doors; their exterior access and interiors are not certified.']
 write(HERE/'landmark_integration_pack.json',pack);write(HERE/'evidence/annex_compile_report.json',sample)
 assert all(p.read_bytes()==v for p,v in before.items()),'Frozen source changed'
 write(HERE/'evidence/overlay_checks.json',{'pass':True,'frozen_sources_unchanged':True,'plan_unchanged':True,'placement_count':len(pack['placements']),'suppressed_buildings':len(suppressed),'obsolete_paths':len(pack['suppress_path_ids']),'new_primary_paths':len(paths),'support_pass':True,'annex_candidate_cells':c['candidate_cells'],'actual_scene_loaded':False})
 print(json.dumps({'path':str((HERE/'landmark_integration_pack.json').relative_to(ROOT)),'placements':len(pack['placements']),'suppress_buildings':len(suppressed),'suppress_paths':len(pack['suppress_path_ids']),'primary_links':len(paths),'annex_candidates':c['candidate_cells']}))
 return pack
if __name__=='__main__':build()
