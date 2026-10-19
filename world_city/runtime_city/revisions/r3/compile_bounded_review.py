"""Compile only frozen manor/woodland correction modules with existing common tools."""
from pathlib import Path
import json,copy,sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.assemble_city import write,sha
from world_city.runtime_city.urban_fabric.revisions.r3.author_overlay import make_master
from voxel_character.common import coordinate_planes,render_data
OUT=ROOT/'world_city/runtime_city/generated/r3_bounded_review'
def main():
 source=ROOT/'world_city/runtime_city/urban_fabric/revisions/r3/generated/overlay.json';d=json.loads(source.read_text());assert d['checks']['valid']
 write(OUT/'source_overlay.snapshot.json',d)
 selected={'UF_ESTATE_01','UF_FOREST_NW'};d['placements']=[p for p in d['placements'] if p['property_id'] in selected];keys={p['asset_key'] for p in d['placements']};pitch={p['asset_key']:p['requested_pitch_m'] for p in d['placements']};assets={}
 for k in sorted(keys):
  m=make_master(d['master_specs'][k]);mp=OUT/'masters'/f'{k}.json';write(mp,m)
  r=coordinate_planes.compile_master(m,{'pitch':pitch[k]},max_candidate_cells=250000,max_output_cells=100000);assert r['valid'],(k,r)
  data=render_data.make_render_data(r);rp=OUT/'renders'/f'{k}.json';write(rp,data)
  assets[k]={'render_path':str(rp.relative_to(ROOT)),'render_sha256':sha(rp),'master_path':str(mp.relative_to(ROOT)),'master_sha256':sha(mp),'bounds':data['bounds'],'cell_count':data['cell_count'],'quad_count':data['quad_count'],'pitch_m':pitch[k]}
 flat=ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json';s=json.loads(flat.read_text());f=json.loads((ROOT/'world_city/runtime_city/revisions/r3/urban_fabric.access_repaired.json').read_text())
 remove={p['id'] for p in f['placements'] if p['property_id'] in selected};assert remove<=set(d['replacement_ledger']['remove_placement_ids'])
 inf=s['infrastructure'];inf['placements']=[p for p in inf['placements'] if p['id'] not in remove]+d['placements'];inf['assets'].update(assets);used={p['asset_key'] for p in inf['placements']};inf['assets']={k:a for k,a in inf['assets'].items() if k in used}
 s['revision']='visual_qa_r3_bounded_manor_forest';s['status']='bounded_repair_actual_visual_review_pending';s['camera_scope']='Stone manor +NWwoodland only; flat comparison, new wholecityconcept/terrain pending'
 s['art_review_stage']='Bounded manor + woodland correction; remaining city and heights still under review'
 s['inspection_cameras']={'woodland_nw':{'position_m':[-570,49,-430],'target_m':[-660,9,-550]},'estate_gate':{'position_m':[192,1.7,-15],'target_m':[204,3,0]}}
 s['visual_revision_sources']={'flat_scene_sha256':sha(flat),'overlay_snapshot_sha256':sha(OUT/'source_overlay.snapshot.json'),'author_sha256':sha(ROOT/'world_city/runtime_city/urban_fabric/revisions/r3/author_overlay.py'),'selected_property_ids':sorted(selected),'removed_original_placements':len(remove),'new_placements':len(d['placements'])}
 write(OUT/'scene.json',s);write(OUT/'compiled_overlay.json',{'assets':assets,'placements':d['placements'],'properties':[p for p in d['property_records'] if p['id'] in selected],'vegetation':[p for p in d['vegetation_land_use'] if p['id'] in selected],'sources':s['visual_revision_sources']})
 print(json.dumps({'scene':str(OUT/'scene.json'),'masters':len(assets),'removed':len(remove),'placed':len(d['placements']),'cells':sum(a['cell_count'] for a in assets.values()),'quads':sum(a['quad_count'] for a in assets.values())},indent=2))
if __name__=='__main__':main()
