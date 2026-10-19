"""R6 review cameras retain the registered concept comparison verbatim."""
import copy

def add_review_cameras(scene):
 out=dict(scene);cameras=copy.deepcopy(scene['inspection_cameras']);out['inspection_cameras']=cameras
 cameras.update(
   merchant_lower=dict(position_m=[215,79,455],target_m=[151,5,348],purpose='Two newly activated attached market-to-port courts and retained circulation.'),
   merchant_north=dict(position_m=[30,77,128],target_m=[-49,5,30],purpose='Two newly activated older/rebuilt merchant courts west of market.'),
   merchant_court_eye=dict(position_m=[-32.2058726585,2.65,-6.9886821322],target_m=[-46.2044802197,2.65,-4.8163593315],eye_height_m=1.65,source_route='MF02_011_BLOCK_011:ALLEY_0_51_+1_wide_early_court:FINITE_PUBLIC_HANDOFF',purpose='Visual view from accepted inner gate seam toward small-goods court. Physics pending.'),
   productive_grounds=dict(position_m=[-45,215,225],target_m=[-235,16,110],purpose='Abbey productive margins and estate-linked grounds in actual city context.'))
 assert cameras['registered']==scene['inspection_cameras']['registered']
 return out
