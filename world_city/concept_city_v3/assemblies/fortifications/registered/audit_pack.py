"""Timed sequential cache replay and bounded native throat/support checks."""
import json,math,resource,time
from pathlib import Path
from resolve_pack import HERE,OUT,ROOT,ref,write,pose,terrain,geo
from voxel_character.common import coordinate_planes,core,render_data

def main(out=OUT):
 start=time.monotonic();path=out/'resolved_placements.json';pack=json.loads(path.read_text());plan=json.loads((ROOT/pack['source_plan']['path']).read_text());assets={x['id']:x for x in pack['assets']};issues=[];replays=[];gates=[]
 assert pack['source_plan']==ref(ROOT/pack['source_plan']['path'])
 for a in pack['assets']:
  assert ref(ROOT/a['source']['path'])==a['source'];assert ref(ROOT/a['cache']['path'])==a['cache'];s=json.loads((ROOT/a['source']['path']).read_text());r=json.loads((ROOT/a['cache']['path']).read_text());assert core.digest(s)==r['master_hash']==a['master_hash']
  if any('/'+tag+'/' in a['source']['path'] for tag in ('placement_r01','placement_r02')):
   t=time.monotonic();c=coordinate_planes.compile_master(s,{'pitch':.5},max_candidate_cells=400000,max_output_cells=200000);assert c['valid'];r2=render_data.make_render_data(c);assert r2==r
   replays.append({'asset_id':a['id'],'candidate_cells':c['candidate_cells'],'seconds':time.monotonic()-t,'output_cells':len(c['cells'])})
 for support in pack['support_evidence']:
  assert support['minimum_sampled_embed_m']>=.499999;assert support['all_samples_reached']
  p=next(x for x in pack['placements'] if x['id']==support['placement_id'])
  for x,y,z in support['footprint_samples_xyz_m']:assert abs(terrain.height_at(x,z)-y)<1e-9
 # Broad-phase against road ribbons for all actual low-level cache envelopes.
 roadrecords=[];index=geo._SpatialIndex(32)
 for road in plan['roads']:
  for i,(a,b) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
   r={'road_id':road['id'],'segment':i,'polygon':geo.road_ribbon(a,b,road['width_m'])};index.add(len(roadrecords),r['polygon']);roadrecords.append(r)
 gateids={x['placement_id'] for x in pack['gates']}
 for p in pack['placements']:
  if p['id'] in gateids:continue
  for i in index.candidates(p['outer_footprint_xz_m']):
   road=roadrecords[i];q=geo.convex_intersection(p['outer_footprint_xz_m'],road['polygon'])
   if len(q)<3 or geo.polygon_area(q)<1e-7:continue
   ys=[terrain.road_height_at(road['road_id'],*v) for v in q]
   if p['world_y_range_m'][1]>min(ys)+.1 and p['world_y_range_m'][0]<max(ys)+2:
    issues.append({'code':'road_walking_height_envelope_intersection','placement_id':p['id'],'role':p['semantic_role'],'road_id':road['road_id'],'segment':road['segment'],'area_m2':geo.polygon_area(q),'polygon_xz_m':q,'road_y_range_m':[min(ys),max(ys)]})
 for gate in pack['gates']:
  p=next(x for x in pack['placements'] if x['id']==gate['placement_id']);s=json.loads((ROOT/p['source']['path']).read_text());c=coordinate_planes.compile_master(s,{'pitch':.5},max_candidate_cells=400000,max_output_cells=200000);pitch=c['pitch'];roads=[roadrecords[i] for i in index.candidates(p['outer_footprint_xz_m']) if roadrecords[i]['road_id']==gate['floor_owner']];hits=[];tested=0
  for row in c['cells']:
   x,y,z=[v*pitch for v in row[:3]];lo=p['position_m'][1]+y;hi=lo+pitch
   if lo>p['position_m'][1]+4 or hi<p['position_m'][1]-1:continue
   poly=[]
   for xx,zz in ((x,z),(x+pitch,z),(x+pitch,z+pitch),(x,z+pitch)):
    v=pose([xx,0,zz],p['position_m'],p['yaw_degrees']);poly.append([v[0],v[2]])
   for road in roads:
    q=geo.convex_intersection(poly,road['polygon'])
    if len(q)<3 or geo.polygon_area(q)<1e-8:continue
    ys=[terrain.road_height_at(road['road_id'],*v) for v in q];tested+=1
    if hi>min(ys)+.1 and lo<max(ys)+2:
     hits.append({'cell':row[:3],'feature':row[6],'road_segment':road['segment'],'intersection_area_m2':geo.polygon_area(q),'cell_y_range_m':[lo,hi],'road_y_range_m':[min(ys),max(ys)]})
  gates.append({'placement_id':p['id'],'candidate_cells':c['candidate_cells'],'tested_cell_road_intersections':tested,'walking_height_hits':hits,'pass':not hits,'scope':'Every occupied0.5m source voxel intersecting the exact road ribbon, from floor+.1 to floor+2m. This is geometry clearance, not a runtime capsule/controller test.'})
 result={'schema':'riverstone.city.native_fortification_audit.v1','source_pack':ref(path),'status':'pass' if not issues and all(g['pass'] for g in gates) else 'fail','hashes_checked':len(pack['assets']),'source_placements_checked':len(pack['placements']),'support_footprints_checked':len(pack['support_evidence']),'support_samples_checked':sum(len(x['footprint_samples_xyz_m']) for x in pack['support_evidence']),'cache_replays':replays,'cache_replay_count':len(replays),'gate_tests':gates,'ordinary_road_envelope_issues':issues,'total_audit_wall_seconds':time.monotonic()-start,'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'compile_replay_seconds':sum(x['seconds'] for x in replays),'whole_wall_compile':False,'actual_scene_or_capsule_test':False}
 write(out/'audit_report.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('cache_replays','gate_tests','ordinary_road_envelope_issues')},indent=2));print('road issues',len(issues),'gate hits',[(g['placement_id'],len(g['walking_height_hits'])) for g in gates]);return result

if __name__=='__main__':
 import sys
 main(HERE/sys.argv[1] if len(sys.argv)>1 else OUT)
