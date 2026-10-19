"""Replace only the fixed bridge in a sealed review scene, with an explicit ledger.
The focused view reuses real terrain/port geometry; no concept or screenshot edits.
"""
import copy,hashlib,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parents[1]
PACK=CITY/'assemblies/waterworks/registered_bridge/drawbridge_candidate/resolved_placements.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def bridge_into_scene(base):
 d=copy.deepcopy(base);p=load(PACK);audit=load(ROOT/p['geometry_audit']['path']);assert audit['valid'],'Bridge geometry audit failed'
 for key in ('candidate','state_contract','geometry_audit','compile_report'):assert sha(ROOT/p[key]['path'])==p[key]['sha256']
 for key,a in p['assets'].items():
  assert sha(ROOT/a['master_path'])==a['master_sha256'];assert sha(ROOT/a['render_path'])==a['render_sha256']
  old=d['common_assets'].get(key);assert not old or old['render_sha256']==a['render_sha256'];d['common_assets'][key]=copy.deepcopy(a)
 removed=set(p['replacement_overlay']['suppress_placement_ids']);actual={q['id'] for q in d['common_instances'] if q['id'] in removed};assert actual==removed,(actual,removed)
 d['common_instances']=[q for q in d['common_instances'] if q['id'] not in removed]
 for q in p['placements']:
  rows=q['transform']['basis'];yaw=math.atan2(rows[0][2],rows[0][0]);d['common_instances'].append(dict(id=q['id'],asset_key=q['asset_key'],position_m=q['position_m'],yaw_rad=yaw,scale=[1,1,1],palette_id='native_drawbridge',palette_override={},source_pack='drawbridge_fixed'))
 keys=('states','motion_samples','barrier_samples','hinge_cover_samples','cycle_stages','bridge_to_world','inspection_vessel','surface_ownership')
 d['bridge_mechanism']={k:copy.deepcopy(p[k]) for k in keys};d['bridge_mechanism']['asset_keys']=list(p['assets'])
 d['bridge_mechanism']['provenance']=dict(source_pack_path=str(PACK.relative_to(ROOT)),source_pack_sha256=sha(PACK),geometry_audit=p['geometry_audit'])
 d['inspection_cameras'].update(bridge_closed=dict(position_m=[180,34,535],target_m=[129,6,491],bridge_state='ROAD_OPEN'),bridge_open=dict(position_m=[180,34,535],target_m=[129,6,491],bridge_state='NAVIGATION_OPEN'),bridge_midpoint=dict(position_m=[180,34,535],target_m=[129,6,491],bridge_state='LIFTING_MIDPOINT'))
 d['counts']['common_instances']=len(d['common_instances']);d['counts']['common_unique_assets']=len(d['common_assets']);d['counts']['bridge_moving_nodes']=len(p['states']['ROAD_OPEN']['movable_placements'])
 d['bridge_promotion_ledger']=dict(parent_geometry_hashes={k:digest(base[k]) for k in ('surfaces','boxes','common_instances','common_assets')},unchanged_surfaces_sha256=digest(d['surfaces']),unchanged_boxes_sha256=digest(d['boxes']),removed_static_ids=sorted(removed),inserted_static_ids=[q['id'] for q in p['placements']],runtime_moving_ids=p['replacement_overlay']['movable_ids_owned_by_mechanism_only'],not_claimed=['Character collision or navigation controller','Vessel roll/drift/flood','Structural load or powered mechanism simulation'])
 assert digest(d['surfaces'])==digest(base['surfaces']) and digest(d['boxes'])==digest(base['boxes'])
 return d
def main():
 focused='--focused' in sys.argv
 parent=CITY/('evidence/visual_registered_common_r2/camera_scene.json' if focused else 'evidence/visual_registered_common_r3/camera_scene.json')
 out=CITY/('evidence/visual_drawbridge_r1' if focused else 'evidence/visual_registered_common_r3')
 out.mkdir(parents=True,exist_ok=True);dest=out/('scene.json' if focused else 'bridge_scene.json')
 if dest.exists():raise ValueError('Preserve existing review scene; select a new revision.')
 d=bridge_into_scene(load(parent));d['bridge_promotion_ledger']['parent_scene']=dict(path=str(parent.relative_to(ROOT)),sha256=sha(parent))
 if focused:
  x0,z0,x1,z1=0,345,250,625
  def near(points):return not(max(q[0] for q in points)<x0 or min(q[0] for q in points)>x1 or max(q[2] for q in points)<z0 or min(q[2] for q in points)>z1)
  for key,verts in d['surfaces'].items():d['surfaces'][key]=[v for i in range(0,len(verts),3) if near(verts[i:i+3]) for v in verts[i:i+3]]
  d['surfaces']={k:v for k,v in d['surfaces'].items() if v}
  d['boxes']=[q for q in d['boxes'] if x0-20<=q['position_m'][0]<=x1+20 and z0-20<=q['position_m'][2]<=z1+20]
  d['common_instances']=[q for q in d['common_instances'] if x0-40<=q['position_m'][0]<=x1+40 and z0-40<=q['position_m'][2]<=z1+40]
  d['bridge_promotion_ledger']['focused_context_selection']=dict(bounds_xz_m=[x0,z0,x1,z1],method='Retain real nearby scene triangles/boxes/instances, without changing their geometry. Original city scene remains sealed.')
  d['counts']['common_instances']=len(d['common_instances']);d['counts']['actual_remaining_proxy_boxes']=len(d['boxes'])
 d['status']='native_lifting_bridge_visual_candidate_no_physics_claim';dest.write_text(json.dumps(d,separators=(',',':'))+'\n')
 (out/'promotion_ledger.json').write_text(json.dumps(d['bridge_promotion_ledger'],indent=2)+'\n');print(json.dumps(dict(path=str(dest),sha256=sha(dest),instances=len(d['common_instances']),moving=d['counts']['bridge_moving_nodes']),indent=2))
if __name__=='__main__':main()
