"""Small common-voxel entry stair and smooth, shadow-only roof proxy.
The house source/cells stay unchanged. Proxy is not visible geometry/collision.
"""
from pathlib import Path
import json,sys,hashlib,math
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'voxel_character/common')]
from core import compile_master
from render_data import make_render_data
from author_house import box

def write(path,data):
 blob=json.dumps(data,sort_keys=True,separators=(',',':'))+'\n'
 if path.exists():
  assert path.read_text()==blob, 'Changed output preserved: '+str(path)
 else:path.write_text(blob)

def main():
 m=json.loads((HERE/'source/house.r04.master.json').read_text())
 steps={'schema':m['schema'],'revision':1,'id':'B_REG_0120_entry_steps_r01','materials':m['materials'], 'components':[{'id':'stairs','parts':[{'id':'solid','pivot':[0,0,0]}],'operations':[box('entry_step_'+str(i),[-1.05,0,7+.3*i],[1.05,.375-.125*i,7+.3*(i+1)],'stone_light') for i in range(3)]}],'instances':[{'id':'stairs','component':'stairs','transform':{'translation':[0,0,0]}}]}
 # Preserve required common metadata from the original master schema.
 for k in ('units','coordinate_system','axes'): 
  if k in m:steps[k]=m[k]
 steps['provenance']={'house_master_sha256':hashlib.sha256((HERE/'source/house.r04.master.json').read_bytes()).hexdigest(),'purpose':'three .125m risers to existing .5m threshold, 2.1m wide; door remains closed'}
 c=compile_master(steps,{'pitch':.025},max_candidate_cells=100000,max_output_cells=100000)
 assert c['valid'],c['constraints']
 r=make_render_data(c); write(HERE/'source/entry_steps.master.json',steps);write(HERE/'generated/entry_steps.render.json',r)
 roof=next(c for c in m['components'] if c['id']=='roof')
 proxies=[o['shape'] for o in roof['operations'] if o['id'] in ['roof_plane_0','roof_plane_1']]
 write(HERE/'source/roof_shadow_proxy.json',{'schema':'riverstone.shadow_extrusions.v1','source_master_sha256':steps['provenance']['house_master_sha256'],'purpose':'smooth underlay only casts shadow; visible .05m tile geometry unchanged and still receives other-object shadows','extrusions':proxies})
 write(HERE/'source/entry_access.json',{'width_m':2.1,'rise_m':.125,'tread_m':.3,'step_count':3,'threshold_height_m':.5,'ramp_z':[7.9,7.0],'ramp_y':[0,.5],'grade_degrees':math.degrees(math.atan2(.5,.9)),'visible_vs_collision_vertical_envelope_max_m':.125,'closed_door':True,'preserve_controller':True,'scope':'sample entrance approach, no interior or whole-city entry pass claim'})
 print(json.dumps({'cells':len(c['cells']),'quads':r['quad_count'],'constraints':c['constraints']}))
if __name__=='__main__':main()
