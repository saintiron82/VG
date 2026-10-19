"""Explicit ordinary-retirement inputs for district consolidation.

A candidate in this ledger is not authorization to erase its floor. Only a
fabric proposal selecting that source ID may activate its finite restoration.
"""
import json
from collections import Counter
from . import author as a
ORDINARY=a.CITY/'assemblies/ordinary/registered/resolved_placements.json'

def build_candidates(scene,plan):
 active={p['id']:p for p in scene['common_instances']if p.get('source_pack')=='ordinary'}
 pack=json.loads(ORDINARY.read_bytes());poses={p['id']:p for p in pack['placements']};source={p['id']:p for p in plan['buildings']};plots={p['id']:p for p in plan['plots']}
 foundations={r['source_mass_id']:r for r in scene['terrain_contract']['ordinary_foundations']}
 access={}
 for r in pack['access_proposals']:access.setdefault(r['source_mass_id'],[]).append(r)
 paths={}
 for r in plan['paths']:
  sid=r.get('owner_building_id',r.get('source_mass_id'))
  if sid:paths.setdefault(sid,[]).append(r)
 rows=[]
 for sid,instance in sorted(active.items()):
  if sid not in poses or sid not in source or sid not in foundations:continue
  p=poses[sid];mass=source[sid];plot=plots[mass['plot_id']];f=foundations[sid];floor=p['pad_floor_y_m']
  if plot.get('block_id')not in a.PRIORITY_BLOCKS:continue
  matching=next((y for y in(1.,2.5)if abs(floor-y)<=a.BAND_TOLERANCE_M),None)
  rows.append(dict(source_id=sid,block_id=plot['block_id'],existing_finished_floor_y_m=floor,matching_level_band_y_m=matching,source_instance=instance,old_terrain_body_hole_polygon_xz_m=f['polygon_xz_m'],actual_native_body_footprint_xz_m=p['actual_body_footprint_xz_m'],actual_native_outer_footprint_xz_m=p['actual_outer_footprint_xz_m'],native_origin_y_m=p['position_m'][1],foundation_proxy=f,old_source_paths=paths.get(sid,[]),actual_old_access_records=access.get(sid,[]),status='MATCHING_FLOOR_RESTORATION_CANDIDATE'if matching is not None else'NONMATCHING_FLOOR_REQUIRES_BOUNDED_SUPPORT_AND_EDGE_REVIEW',activation=False,restoration_conditions=['Explicitly selected source ID and old foundation proxy retirement.','Use exact exposed old body/door owners; subtract all retained traffic/water/native owners.','Check existing source-plane boundary and shared seams in the district union. Missing exposed terrain alone is not evidence of a hole.','Keep new native holes empty; restore only the obsolete exposed parts.','Any unchanged/reduced discrete nonwalking edge needs explicit side geometry; a new public or gate crossing must be continuous.']))
 return dict(schema='riverstone.r17.ordinary_retirement_candidates.v1',base_scene_sha256=a.SCENE_SHA256,ordinary_pack=dict(path=str(ORDINARY.relative_to(a.ROOT)),sha256=a.sha(ORDINARY)),rows=rows,summary=dict(total=len(rows),matching_floor=sum(r['matching_level_band_y_m']is not None for r in rows),by_block=dict(Counter(r['block_id']for r in rows))),activation=False)
if __name__=='__main__':
 p=a.HERE/'retirement_candidates.json'
 if p.exists():raise SystemExit('Refusing to overwrite retirement candidates')
 d=build_candidates(a.load_scene(),json.loads(a.PLAN_PATH.read_bytes()));p.write_text(json.dumps(d,separators=(',',':'))+'\n');print(d['summary']);print(a.sha(p))
