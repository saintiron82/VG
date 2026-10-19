"""Resolve another eligible merchant recipe against this finite immutable cache.

This API does not select land, change a source plan, compile or claim ground
eligibility. Callers must supply an independently approved recipe/frame.
"""
import hashlib,json
from .grammar import HERE,ROOT,ref

def resolve_recipe_ranges(recipe):
 report=json.loads((HERE/'compile_report.json').read_text());members={p['id']:p for p in recipe['placements']};out=[];unresolved=[]
 for group in recipe['groups']:
  ms=[members[k] for k in group['member_ids']]
  if len(ms)==1:
   member=ms[0];asset=recipe['assets'][member['asset_key']]
   if ref(ROOT/asset['render_path'])['sha256']!=asset['render_sha256']:raise ValueError('existing source render changed')
   out.append(dict(id=group['id'],asset_key=member['asset_key'],position_m=member['position_m'],yaw_rad=member['yaw_rad'],scale=[1,1,1],source_member_ids=group['member_ids'],render=ref(ROOT/asset['render_path']),kind='existing_native_single'))
   continue
  entries=[dict(asset_key=m['asset_key'],translation=[m['local_center_xz_m'][0],0,m['local_center_xz_m'][1]],yaw_rad=m.get('local_yaw_rad',0)) for m in ms];entries.sort(key=lambda x:(x['translation'],x['asset_key']));key='merchant_native_union_'+hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()[:14]
  if key not in report['assets']:
   unresolved.append(dict(group_id=group['id'],required_signature=key,reason='No exact native composition in this fixed three-range cache. No automatic new compile.'));continue
  a=report['assets'][key]
  if ref(ROOT/a['render_path'])['sha256']!=a['render_sha256']:raise ValueError('shared range render changed')
  out.append(dict(id=group['id'],asset_key=key,position_m=[recipe['origin_xz_m'][0],recipe['floor_y_m']-.5,recipe['origin_xz_m'][1]],yaw_rad=recipe['yaw_rad'],scale=[1,1,1],source_member_ids=group['member_ids'],render=ref(ROOT/a['render_path']),kind='existing_native_common_union'))
 return dict(property_id=recipe['id'],placements=out,unresolved=unresolved,compile_count=0,land_and_ground_status='Caller must provide explicit finite road/water/access and finished-floor/retaining eligibility.',cache=ref(HERE/'compile_report.json'))
