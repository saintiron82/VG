#!/usr/bin/env python3
"""Small synthetic harness regression, explicitly not city acceptance evidence."""
import json,pathlib,hashlib,subprocess,os,math
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 out=H/'synthetic_smoke_r01';out.mkdir();(out/'evidence').mkdir();(out/'geometry').mkdir()
 for n in ['Traversal.gd','Traversal.tscn','RenderData.gd','project.godot','CartClearance.gd','CartClearance.tscn']:(out/n).write_bytes((H/n).read_bytes())
 floor=out/'geometry/flat.json';floor.write_text(json.dumps({'triangles':[[[-20,0,-20],[20,0,-20],[20,0,20]],[[-20,0,-20],[20,0,20],[-20,0,20]]],'fixture':'synthetic_regression_only'}))
 sloped=out/'geometry/sloped.json';sloped.write_text(json.dumps({'triangles':[[[-20,-2,-20],[20,2,-20],[20,2,20]],[[-20,-2,-20],[20,2,20],[-20,-2,20]]],'fixture':'synthetic_regression_only'}))
 assets={};placements={}
 for key,p in [('flat',floor),('sloped',sloped)]:assets[key]={'render_path':str(p.relative_to(ROOT)),'render_sha256':sha(p),'collision_format':'actual_scene_triangles'};placements[key]={'id':key,'asset_key':key,'position_m':[0,0,0],'category':'synthetic_unit_floor','collision_layer':1}
 def box(id,lo,hi):return {'id':id,'position_m':[0,0,0],'yaw_rad':0,'boxes':[{'min':lo,'max':hi}],'collision_layer':3}
 buildings={'low':box('low',[-.1,0,-3],[.1,.4,3]),'high':box('high',[-.1,2.1,-3],[.1,2.5,3]),'left':box('left',[-3,0,-3],[3,3,-.8]),'right':box('right',[-3,0,.8],[3,3,3])}
 routes=[]
 def route(id,pts,ground='flat',obs=[]):routes.append({'id':id,'kind':'synthetic_unit_test','points':pts,'length_m':sum(math.dist(a,b)for a,b in zip(pts,pts[1:])),'placement_ids':[ground],'building_ids':obs,'source_road_ids':[],'test_scope':'Synthetic harness regression only; no city gate claim','cart_test':True})
 route('STRAIGHT',[[-7,0,0],[7,0,0]])
 route('NINETY_DEG_TURN',[[-7,0,0],[0,0,0],[0,0,7]])
 route('TEN_PERCENT_SLOPE',[[-7,-.7,0],[7,.7,0]],'sloped')
 route('LOW_OBSTRUCTION',[[-7,0,0],[7,0,0]],obs=['low'])
 route('OVERHEAD_BEAM',[[-7,0,0],[7,0,0]],obs=['high'])
 route('TOO_NARROW',[[-7,0,0],[7,0,0]],obs=['left','right'])
 d={'repo_root':str(ROOT),'sources':{},'implementation_hashes':{str((out/n).relative_to(ROOT)):sha(out/n)for n in ['Traversal.gd','RenderData.gd','CartClearance.gd']},'assets':assets,'placements':placements,'buildings':buildings,'routes':routes,'coverage':{'scope':'Synthetic unit regression only'},'assumptions':[],'cart_fixture':json.loads((H/'INPUT_CONTRACT.json').read_bytes())['cart_fixture']}
 (out/'prepared.json').write_text(json.dumps(d));env=dict(os.environ,GODOT_SILENCE_ROOT_WARNING='1')
 for k,v in [('XDG_CACHE_HOME','cache'),('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config')]:p=out/'.runtime'/v;p.mkdir(parents=True);env[k]=str(p)
 with(out/'engine.log').open('w')as f:r=subprocess.run(['godot','--headless','--disable-render-loop','--fixed-fps','60','--path',str(out),'res://CartClearance.tscn','--','--prepared='+str(out/'prepared.json'),'--report='+str(out/'evidence/cart.json')],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=90)
 report=json.loads((out/'evidence/cart.json').read_bytes());actual={r['id']:r['status']for r in report['routes']};expected={'STRAIGHT':['clear_supported'],'NINETY_DEG_TURN':['clear_supported'],'TEN_PERCENT_SLOPE':['clear_supported'],'LOW_OBSTRUCTION':['envelope_overlap','swept_envelope_blocked'],'OVERHEAD_BEAM':['envelope_overlap','swept_envelope_blocked'],'TOO_NARROW':['envelope_overlap','swept_envelope_blocked']};checks={k:actual.get(k)in v for k,v in expected.items()};result={'scope':'Synthetic unit regression, not gate acceptance','pass':all(checks.values()),'checks':checks,'actual_statuses':actual,'engine_exit_code':r.returncode};(out/'unit_results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return 0 if result['pass']else 1
if __name__=='__main__':raise SystemExit(main())
