"""Compile bounded infrastructure source through the unchanged common pipeline."""
from pathlib import Path
import json,sys,time,hashlib,collections
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.assemble_city import write,sha
from world_city.runtime_city.infrastructure.author import build_infrastructure,make_master
from voxel_character.common import coordinate_planes,render_data
HERE=Path(__file__).resolve().parent;OUT=HERE/'generated'/'r1'

def main():
 plan=json.loads((ROOT/'world_city/data/city_brief.v2.json').read_text());inf=build_infrastructure(plan)
 assets={};empty=[]
 pitch_by_key={p['asset_key']:p['requested_pitch_m'] for p in inf['placements']}
 for i,(key,spec) in enumerate(inf['master_specs'].items()):
  master=make_master({'asset_id':key,**spec});mp=OUT/'infrastructure_masters'/f'{key}.json';write(mp,master)
  pitch=pitch_by_key[key];rp=OUT/'infrastructure_renders'/f'{key}.json';cp=OUT/'infrastructure_cache'/f'{key}.json'
  fingerprint={'master':sha(mp),'pitch':pitch,'core':sha(ROOT/'voxel_character/common/core.py'),'planes':sha(ROOT/'voxel_character/common/coordinate_planes.py'),'exporter':sha(ROOT/'voxel_character/common/render_data.py'),'mesher':sha(ROOT/'voxel_character/tools/mesh.py')}
  if cp.exists():
   cached=json.loads(cp.read_text())
   if cached['key']==fingerprint and (cached.get('empty') or rp.exists() and sha(rp)==cached['render_sha256']):
    if cached.get('empty'):empty.append(key)
    else:assets[key]=cached
    continue
  result=coordinate_planes.compile_master(master,{'pitch':pitch},max_candidate_cells=1500000,max_output_cells=250000)
  if not result['valid']:raise ValueError((key,result['constraints']))
  if not result['cells']:
   empty.append(key);write(cp,{'key':fingerprint,'empty':True,'reason':'valid_center_sampled_subcell_shoreline_sliver'});continue
  render=render_data.make_render_data(result);write(rp,render)
  stat={'key':fingerprint,'render_path':str(rp.relative_to(ROOT)),'render_sha256':sha(rp),'master_path':str(mp.relative_to(ROOT)),'master_sha256':sha(mp),'bounds':render['bounds'],'cell_count':len(result['cells']),'quad_count':render['quad_count'],'pitch_m':pitch};assets[key]=stat;write(cp,stat)
  if i%100==0:print(json.dumps({'index':i,'key':key,'cells':stat['cell_count']}),flush=True)
 allplacements=inf['placements'];inf['placements']=[p for p in allplacements if p['asset_key'] not in empty];inf['sampled_empty_keys']=empty;inf['sampled_empty_placements']=[p['id'] for p in allplacements if p['asset_key'] in empty]
 fountain=json.loads((ROOT/'voxel_character/common/assets/fountain/compiled_pitch_0.1.json').read_text());fr=render_data.make_render_data(fountain);fp=OUT/'infrastructure_renders/fountain.json';write(fp,fr)
 assets['fountain']={'render_path':str(fp.relative_to(ROOT)),'render_sha256':sha(fp),'bounds':fr['bounds'],'cell_count':fr['cell_count'],'quad_count':fr['quad_count'],'pitch_m':.1}
 inf['placements'].append({'id':'F_MARKET_FOUNTAIN','asset_key':'fountain','position_m':[-20,0,0],'yaw_deg':0,'category':'fountain','render_offset_y_m':0})
 inf['assets']=assets;write(OUT/'infrastructure.json',inf)
 print(json.dumps({'assets':len(assets),'placements':len(inf['placements']),'empty_keys':empty,'quads':sum(a['quad_count'] for a in assets.values())}),flush=True)
if __name__=='__main__':main()
