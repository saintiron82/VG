"""Resolve the finite five-family grammar against immutable native caches only."""
import json
from .grammar import HERE,ROOT,xform
from .prepare_cache import canonical

def resolve_recipe_ranges(recipe):
 """Return rigid group placements/assets; raise for any uncached combination.

 Caller owns source-land/road/water/terrain eligibility. This function creates no
 files and does not compile, scale, place a scene or approve ground ownership.
 """
 b=json.loads((HERE/'compile_budget.json').read_text());c=json.loads((HERE/'compile_report.json').read_text());known={};assets=b['reused_assets']|c['assets'];oldbase=HERE.parent/'merchant_block011';old=json.loads((oldbase/'compile_budget.json').read_text())
 for key,v in b['variants'].items():known[v['signature']]=(key,[0,0,0])
 for key,v in old['variants'].items():
  signature,normal,anchor=canonical(v['entries'])
  if key in assets:known[signature]=(key,anchor)
 members={p['id']:p for p in recipe['placements']};out=[];used={}
 for group in recipe['groups']:
  ms=[members[k] for k in group['member_ids']];entries=[dict(asset_key=p['asset_key'],translation=[p['local_center_xz_m'][0],0,p['local_center_xz_m'][1]],yaw_rad=p['local_yaw_rad']) for p in ms];signature,normal,anchor=canonical(entries)
  if len(ms)==1:
   key=ms[0]['asset_key'];position=ms[0]['position_m'];yaw=ms[0]['yaw_rad']
  else:
   if signature not in known:raise ValueError('No frozen cache for requested native combination: '+signature)
   key,cache_anchor=known[signature];delta=[anchor[k]-cache_anchor[k] for k in range(3)];center=xform([delta[0],delta[2]],recipe['origin_xz_m'],recipe['yaw_rad']);position=[center[0],recipe['floor_y_m']-.5,center[1]];yaw=recipe['yaw_rad']
  if key not in assets:raise ValueError('Native cache asset is not in the frozen catalog: '+key)
  used[key]=assets[key];out.append(dict(id=group['id'],asset_key=key,position_m=position,yaw_rad=yaw,scale=[1,1,1],property_id=recipe['id'],source_member_ids=group['member_ids'],finished_floor_y_m=recipe['floor_y_m'],palette_id=ms[0]['roof_palette']))
 return dict(placements=out,assets=used,compile_count=0,terrain_approval=False)
