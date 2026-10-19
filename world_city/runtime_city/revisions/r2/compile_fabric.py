"""Compile cached property/vegetation modules through the unchanged common code."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT));OUT=ROOT/'world_city/runtime_city/generated/r2'
from world_city.runtime_city.assemble_city import sha,write
from voxel_character.common import coordinate_planes,render_data

def main():
 from world_city.runtime_city.urban_fabric.author import make_master
 source=ROOT/'world_city/runtime_city/urban_fabric/generated/urban_fabric.json';data=json.loads(source.read_text())
 assert data['checks']['valid'];data['compiled_source_sha256']=sha(source);assets={}
 pitch_by_key={p['asset_key']:p['requested_pitch_m'] for p in data['placements']}
 for key,spec in data['master_specs'].items():
  master=make_master(spec);mp=OUT/'fabric_masters'/f'{key}.json';write(mp,master);pitch=pitch_by_key[key]
  rp=OUT/'fabric_renders'/f'{key}.json';cp=OUT/'fabric_cache'/f'{key}.json'
  fingerprint={'master':sha(mp),'pitch':pitch,'core':sha(ROOT/'voxel_character/common/core.py'),'planes':sha(ROOT/'voxel_character/common/coordinate_planes.py'),'exporter':sha(ROOT/'voxel_character/common/render_data.py'),'mesher':sha(ROOT/'voxel_character/tools/mesh.py')}
  if cp.exists() and rp.exists():
   c=json.loads(cp.read_text())
   if c['key']==fingerprint and c['render_sha256']==sha(rp):assets[key]=c;continue
  start=time.monotonic();result=coordinate_planes.compile_master(master,{'pitch':pitch},max_candidate_cells=2000000,max_output_cells=500000)
  if not result['valid']:raise ValueError((key,result.get('constraints')))
  render=render_data.make_render_data(result);write(rp,render)
  c={'key':fingerprint,'render_path':str(rp.relative_to(ROOT)),'render_sha256':sha(rp),'master_path':str(mp.relative_to(ROOT)),'master_sha256':sha(mp),'bounds':render['bounds'],'cell_count':render['cell_count'],'quad_count':render['quad_count'],'pitch_m':pitch,'seconds':time.monotonic()-start};assets[key]=c;write(cp,c)
  print(json.dumps({'key':key,'cells':c['cell_count'],'quads':c['quad_count']}),flush=True)
 data['assets']=assets;write(OUT/'urban_fabric.json',data)
 print(json.dumps({'masters':len(assets),'placements':len(data['placements']),'source_sha256':data['compiled_source_sha256']}),flush=True)
if __name__=='__main__':main()
