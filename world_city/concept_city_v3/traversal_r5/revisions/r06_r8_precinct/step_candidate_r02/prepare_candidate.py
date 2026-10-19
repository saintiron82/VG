"""Explicit separately versioned, bounded .18 m capability candidate."""
import pathlib,json,hashlib,copy,math
H=pathlib.Path(__file__).resolve().parent;OLD=H.parent/'bank_r01';ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def main():
 for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','project.godot','run.sh']:(H/n).write_bytes((OLD/n).read_bytes())
 original=(OLD/'Traversal.gd').read_text();needle='\tbody.move_and_slide()\n\troute_frames+=1';assert original.count(needle)==1
 original=original.replace('no height resampling or step-up','no height resampling; explicit bounded swept-step candidate')
 candidate=original.replace(needle,'\tcandidate_stair_move(delta,offset)\n\tif stage=="finished":return\n\troute_frames+=1')+(H/'step_methods.gd.txt').read_text()
 (H/'StepTraversal.gd').write_text(candidate);(H/'StepTraversal.tscn').write_text((OLD/'Traversal.tscn').read_text().replace('res://Traversal.gd','res://StepTraversal.gd'))
 (H/'PauseTraversal.gd').write_text((OLD/'PauseTraversal.gd').read_text().replace('extends "res://Traversal.gd"','extends "res://StepTraversal.gd"'));(H/'PauseTraversal.tscn').write_bytes((OLD/'PauseTraversal.tscn').read_bytes())
 run=(OLD/'run_capture.py').read_text().replace("scene='Traversal.tscn'if mode=='baseline'else 'PauseTraversal.tscn'","scene='StepTraversal.tscn'if mode=='baseline'else 'PauseTraversal.tscn'");(H/'run_capture.py').write_text(run)
 d=json.loads((OLD/'prepared.json').read_bytes())
 for id,height,ceiling in [('NEGATIVE_OVERHEIGHT_025',.25,False),('NEGATIVE_LOW_HEADROOM',.15,True)]:
  key='CONTROL:'+id;boxes=[{'min':[-3,-.5,-2],'max':[0,0,2]},{'min':[0,-.5,-2],'max':[3,height,2]}]
  if ceiling:boxes.append({'min':[-.5,1.9,-2],'max':[3,2.2,2]})
  d['buildings'][key]={'id':key,'position_m':[0,0,0],'yaw_rad':0,'boxes':boxes,'collision_layer':3}
  r={'id':id,'kind':'finite_capability_negative_control','group':'synthetic_control','points':[[-2,0,0],[2,height,0]],'length_m':math.hypot(4,height),'source_road_ids':[],'test_scope':'Explicit finite analytical box control, separate from actual city geometry.','minimum_allowed_feet_y_m':-1,'placement_ids':[],'building_ids':[key],'expected_failure':'blocked','expected_contact_id':key};d['routes'].append(r)
 d['sources']['bank_original_failure']={'path':str(OLD/'freeze_baseline.json'),'sha256':sha(OLD/'freeze_baseline.json')};d['sources']['step_candidate_spec']={'path':str(H.parent/'step_capability_proposal.json'),'sha256':sha(H.parent/'step_capability_proposal.json')}
 d['coverage'].update(cases=18,baseline_cases=16,stop_restart_cases=2,capability_candidate={'status':'unexecuted','max_step_up_m':.18,'max_step_down_m':.18,'original_controller_preserved':True,'native_stairs_remain_native':True,'negative_controls_added':['.25 m riser','.15 m step beneath1.9 m ceiling']})
 d['assumptions']=['Explicit bounded swept up/forward/down and down-step candidate, with original movement settings and native geometry.','No ramp collision, route assignment, infinite support or automatic success; strict support checks unchanged.','All exact baseline routes retained; synthetic overheight/headroom tests are finite isolated negative fixtures.']
 d['implementation_hashes'].update({str(p.relative_to(ROOT)):sha(p)for p in H.iterdir()if p.is_file()});write(H/'prepared.json',d)
 write(H/'evidence/controller_delta.json',{'original_sha256':sha(H/'Traversal.gd'),'candidate_sha256':sha(H/'StepTraversal.gd'),'walking_callsite_count':1,'preserved_original_bytes':sha(H/'Traversal.gd')==sha(OLD/'Traversal.gd'),'delta':'Single walking move_and_slide call delegated to bounded sweep helper; all original controller constants and strict acceptance preserved.','candidate_methods_sha256':sha(H/'step_methods.gd.txt'),'cases':18})
 print('CANDIDATE_READY',sha(H/'prepared.json'))
if __name__=='__main__':main()
