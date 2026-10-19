"""Bounded cached R2 compile, delegated to the unchanged common voxel pipeline."""
from pathlib import Path
import argparse,copy,json,sys,time
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT));HERE=Path(__file__).parent
from world_city.runtime_city.assemble_city import write,sha
from voxel_character.common import coordinate_planes,render_data
OUT=ROOT/'world_city/runtime_city/generated/r2'

def compile_one(spec,pitch=.5):
 if spec['family']!='ordinary_r2':raise ValueError('Reuse existing verified r1 assets for other families')
 from world_city.runtime_city.archetypes.ordinary_r2 import make_master
 params={k:v for k,v in spec.items() if k not in ['family','derived_height_m']}
 master=make_master(params);key=spec['asset_id'];mp=OUT/'masters'/f'{key}.json';write(mp,master)
 rp=OUT/'renders'/f'{key}_{pitch}.json';cp=OUT/'cache'/f'{key}_{pitch}.json'
 fp={'master':sha(mp),'pitch':pitch,'compiler':sha(ROOT/'voxel_character/common/core.py'),'planes':sha(ROOT/'voxel_character/common/coordinate_planes.py'),'exporter':sha(ROOT/'voxel_character/common/render_data.py'),'mesher':sha(ROOT/'voxel_character/tools/mesh.py')}
 if cp.exists() and rp.exists():
  old=json.loads(cp.read_text())
  if old['key']==fp and old['render_sha256']==sha(rp):return old
 start=time.monotonic();result=coordinate_planes.compile_master(master,{'pitch':pitch},max_candidate_cells=6500000,max_output_cells=1600000)
 if not result['valid']:raise ValueError((key,result.get('constraints')))
 render=render_data.make_render_data(result);write(rp,render)
 stat={'key':fp,'render_path':str(rp.relative_to(ROOT)),'render_sha256':sha(rp),'master_path':str(mp.relative_to(ROOT)),'master_sha256':sha(mp),'cell_count':render['cell_count'],'quad_count':render['quad_count'],'bounds':render['bounds'],'seconds':round(time.monotonic()-start,3),'constraints':result.get('constraints',{}),'author_metadata':master.get('metadata',{})}
 write(cp,stat);return stat

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,default=HERE/'authoring_plan.base.json');ap.add_argument('--limit',type=int);a=ap.parse_args()
 scene=json.loads(a.plan.read_text());pending=[(k,v) for k,v in scene['asset_specs'].items() if v['family']=='ordinary_r2']
 for n,(key,spec) in enumerate(pending):
  if a.limit is not None and n>=a.limit:break
  stat=compile_one(spec);scene['assets'][key]={'coarse':stat}
  print(json.dumps({'n':n,'of':len(pending),'key':key,'cells':stat['cell_count'],'quads':stat['quad_count'],'seconds':stat['seconds']}),flush=True)
 scene['catalog_complete']=set(scene['assets'])==set(scene['asset_specs'])
 for i in scene['instances']:
  if i['asset_key'] not in scene['assets']:continue
  resources=scene['assets'][i['asset_key']];bounds=[r['bounds'] for r in resources.values()]
  i['local_bounds']={'min':[min(b['min'][j] for b in bounds) for j in range(3)],'max':[max(b['max'][j] for b in bounds) for j in range(3)]}
 scene['status']='compiled_pending_property_topography_integration_and_validation'
 write(OUT/'scene.buildings.json',scene)
 print(json.dumps({'catalog_complete':scene['catalog_complete'],'resources':len(scene['assets']),'instances':len(scene['instances'])}),flush=True)
if __name__=='__main__':main()
