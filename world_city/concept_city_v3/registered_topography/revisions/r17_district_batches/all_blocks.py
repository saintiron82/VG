"""One actual-R7 index for every remaining ordinary body and block floor band."""
import json,time
from collections import Counter,defaultdict
from . import author as a,retirement
from .audit_retired_boundaries import audit

def build(scene,plan):
 start=time.monotonic();active={p['id']:p for p in scene['common_instances']if p.get('source_pack')=='ordinary'}
 pack=json.loads(retirement.ORDINARY.read_bytes());poses={p['id']:p for p in pack['placements']};source={p['id']:p for p in plan['buildings']};plots={p['id']:p for p in plan['plots']};foundations={r['source_mass_id']:r for r in scene['terrain_contract']['ordinary_foundations']};access=defaultdict(list);paths=defaultdict(list)
 for r in pack['access_proposals']:access[r['source_mass_id']].append(r)
 for r in plan['paths']:
  sid=r.get('owner_building_id',r.get('source_mass_id'))
  if sid:paths[sid].append(r)
 rows=[]
 for sid,instance in sorted(active.items()):
  if sid not in poses or sid not in source or sid not in foundations:continue
  p=poses[sid];plot=plots[source[sid]['plot_id']];f=foundations[sid];floor=p['pad_floor_y_m']
  rows.append(dict(source_id=sid,block_id=plot.get('block_id'),existing_finished_floor_y_m=floor,matching_level_band_y_m=floor,standard_lower_city_band=any(abs(floor-y)<=a.BAND_TOLERANCE_M for y in (1.,2.5,4.)),source_instance=instance,old_terrain_body_hole_polygon_xz_m=f['polygon_xz_m'],actual_native_body_footprint_xz_m=p['actual_body_footprint_xz_m'],actual_native_outer_footprint_xz_m=p['actual_outer_footprint_xz_m'],native_origin_y_m=p['position_m'][1],foundation_proxy=f,old_source_paths=paths[sid],actual_old_access_records=access[sid],activation=False))
 ledger=dict(schema='riverstone.r17.all_block_retirement_candidates.v1',base_scene_sha256=a.SCENE_SHA256,ordinary_pack=dict(path=str(retirement.ORDINARY.relative_to(a.ROOT)),sha256=a.sha(retirement.ORDINARY)),rows=rows,scope='Every active ordinary instance with an exact original body owner. Floor label alone is not permission to restore; boundary proof is required.',activation=False)
 index=a.TriangleIndex(scene,[r['old_terrain_body_hole_polygon_xz_m']for r in rows]);proof=[audit(index,r)for r in rows];byblock=defaultdict(lambda:dict(active_ordinary=0,complete_body_boundaries=0,blocked_body_boundaries=0,level_floor_counts=Counter(),complete_source_ids=[],blocked_source_ids=[]))
 for r,p in zip(rows,proof):
  d=byblock[r['block_id']];d['active_ordinary']+=1
  if p['status']=='COMPLETE_LEVEL_BODY_BOUNDARY':d['complete_body_boundaries']+=1;d['complete_source_ids'].append(r['source_id']);d['level_floor_counts'][str(round(r['existing_finished_floor_y_m'],7))]+=1
  else:d['blocked_body_boundaries']+=1;d['blocked_source_ids'].append(r['source_id'])
 return ledger,dict(schema='riverstone.r17.all_block_body_boundary_audit.v1',base_scene_sha256=a.SCENE_SHA256,rows=proof,blocks=dict(byblock),summary=dict(active_ordinary=len(rows),complete_level=sum(r['status']=='COMPLETE_LEVEL_BODY_BOUNDARY'for r in proof),indexed_triangles=len(index.rows),seconds=time.monotonic()-start),limits=['Exact old-body exterior seams only; final native, door, full-width public and retained-side tests remain mandatory.','Nonmatching slopes are explicit held owners, never flat-band restoration.','No ordinary domain exists in protected market BLOCK_012.'],activation=False)
if __name__=='__main__':
 folder=a.HERE/'all_blocks_r01'
 if folder.exists():raise SystemExit('Preserve previous all-block evidence')
 folder.mkdir();ledger,proof=build(a.load_scene(),json.loads(a.PLAN_PATH.read_bytes()));lp=folder/'retirement_candidates.json';lp.write_text(json.dumps(ledger,separators=(',',':'))+'\n');proof['retirement_candidates_sha256']=a.sha(lp);pp=folder/'body_boundary_audit.json';pp.write_text(json.dumps(proof,separators=(',',':'))+'\n');print(proof['summary']);print({k:(v['complete_body_boundaries'],v['blocked_body_boundaries'],v['level_floor_counts'])for k,v in proof['blocks'].items()});print(a.sha(lp),a.sha(pp))
