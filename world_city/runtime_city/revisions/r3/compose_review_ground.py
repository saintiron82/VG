"""One common visible ground owner for manor paving and garden paths.
No depth offset, no runtime cell edits. Original modules retained as provenance.
"""
from pathlib import Path
import json,copy,sys,math
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.assemble_city import write,sha
from world_city.runtime_city.topography.integrate import make_ground_master,placement_polygon,polygon_bounds
from world_city.runtime_city.topography.author import default_field
from world_city.runtime_city.checks.placement import positive_area_overlap
from voxel_character.common import coordinate_planes,render_data
OUT=ROOT/'world_city/runtime_city/generated/r3_composed_review'
def compile_asset(key,master,pitch):
 mp=OUT/'masters'/f'{key}.json';rp=OUT/'renders'/f'{key}.json';write(mp,master)
 result=coordinate_planes.compile_master(master,{'pitch':pitch},max_candidate_cells=2000000,max_output_cells=250000);assert result['valid'],(key,result)
 r=render_data.make_render_data(result);write(rp,r)
 return {'master_path':str(mp.relative_to(ROOT)),'master_sha256':sha(mp),'render_path':str(rp.relative_to(ROOT)),'render_sha256':sha(rp),'bounds':r['bounds'],'cell_count':r['cell_count'],'quad_count':r['quad_count'],'pitch_m':pitch}
def main():
 source=ROOT/'world_city/runtime_city/generated/r3_bounded_review/scene.camera_review2.json';s=json.loads(source.read_text());inf=s['infrastructure'];owners=[];remove=set();gardens=[]
 for p in inf['placements']:
  if p.get('property_id')!='UF_ESTATE_01':continue
  if p['category']=='estate_service_court':
   owners.append({'id':p['id'],'polygon_xz_m':p['footprint_xz_m'],'material':'stone_dark'});remove.add(p['id'])
  if p['category']=='estate_formal_garden':
   owners.append({'id':p['id']+':ground_paths','polygon_xz_m':p['footprint_xz_m'],'material':'stone_light'});gardens.append(p)
 # Raise no faces. Composite only the source-material ownership of the existing terrain.
 selected=[]
 for p in inf['placements']:
  if p['category']!='terrain':continue
  poly=placement_polygon(p)[0]
  if any(positive_area_overlap(poly,o['polygon_xz_m'],0) for o in owners):selected.append(p)
 assert selected
 added=[];records=[]
 for p in selected:
  bounds=polygon_bounds(placement_polygon(p)[0]);master=make_ground_master(bounds,owners,default_field(),pitch=.5,depth=4.)
  # This bounded manor is H0; source field is asserted rather than accidentally projecting unrelated terrain.
  assert all(abs(default_field().height(x,z))<1e-9 for x,z in placement_polygon(p)[0])
  key='r3_court_ground_'+p['id'].replace(':','_');inf['assets'][key]=compile_asset(key,master,.5);remove.add(p['id'])
  added.append({'id':'R3:'+key,'asset_key':key,'position_m':[0,0,0],'yaw_deg':0,'category':'owned_court_ground','world_coordinate_geometry':True,'stream_chunk_xz':p['stream_chunk_xz'],'requested_pitch_m':.5,'collision_enabled':False,'collision_policy':'natural ground uses finite source-grade proxy; visual compositing only'})
  records.append({'replaced_terrain_id':p['id'],'asset_key':key,'bounds_xz_m':bounds,'shared_top_y_m':0,'same_global_origin':[0,0,0]})
 for p in gardens:
  a=inf['assets'][p['asset_key']];master=json.loads((ROOT/a['master_path']).read_text());removed=[]
  for c in master['components']:
   old=c['operations'];removed.extend(o['id'] for o in old if o.get('feature')=='garden_paths');c['operations']=[o for o in old if o.get('feature')!='garden_paths']
  assert removed
  master['metadata']['derived_from_source_master_sha256']=a['master_sha256'];master['metadata']['ground_path_operations_owned_by_composite']=removed
  key=p['asset_key']+'_raised_only';inf['assets'][key]=compile_asset(key,master,.5);p['asset_key']=key;p['master_key']=key
 inf['placements']=[p for p in inf['placements'] if p['id'] not in remove]+added;used={p['asset_key'] for p in inf['placements']};inf['assets']={k:v for k,v in inf['assets'].items() if k in used}
 s['revision']='visual_qa_r3_composed_court';s['ground_ownership_revision']={'source_scene_sha256':sha(source),'single_visible_ground_owner':True,'removed_coplanar_paving_modules':sorted(remove),'replacement_tiles':records,'draw_offset_added_m':0,'source_geometry_only':True}
 write(OUT/'scene.ground_composed.json',s);write(OUT/'ground_ownership.json',s['ground_ownership_revision']);print(json.dumps({'tiles':len(selected),'owners':len(owners),'garden_bases_removed':len(gardens),'removed_placements':len(remove),'output':str(OUT/'scene.ground_composed.json')},indent=2))
if __name__=='__main__':main()
