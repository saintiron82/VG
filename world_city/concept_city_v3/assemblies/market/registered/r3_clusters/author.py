"""Larger native stall modules in paired functional rows; unchanged public route."""
import json,hashlib,copy,math,time,resource
from pathlib import Path
from voxel_character.common import coordinate_planes,render_data
from world_city.runtime_city.urban_fabric.author import make_master
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.assemblies.market.registered.author import bounds_poly
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[3];ROOT=CITY.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def area(p):return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]+p[:1])))/2
def main():
 oldpath=HERE.parent/'resolved_placements.json';old=json.loads(oldpath.read_bytes());plan=json.loads((CITY/'registered_source/plan.json').read_bytes());site=next(x for x in plan['spaces'] if x['id']=='SITE_MARKET');replacement=old['access_overlay']['replace_roads'][0];roads=[replacement if r['id']==replacement['id'] else r for r in plan['roads']];reserved=[]
 for r in roads:
  for a,b in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):reserved.append(geo.road_ribbon(a,b,r['width_m']))
 fountain=copy.deepcopy(old['placements'][0]);cx,_,cz=fountain['position_m'];assets={'fountain':old['assets']['fountain']};report=[]
 for key,cloth,w in [('cloth6',True,6),('timber6',False,6),('cloth8',True,8)]:
  spec=dict(kind='market_stall',width_m=w,depth_m=4,height_m=3.25,cloth=cloth);m=make_master(spec);m['id']='registered_market_'+key;m['metadata']['reuse']='existing urban_fabric.make_master parameterized canopy/posts/counter/wares, unchanged common compiler'
  if w==8:
   for side in (-1,1):m['components'][0]['operations'].append(dict(id='center_brace_'+str(side),part='solid',action='paint',material='timber',shape=dict(kind='box',min=[-.125,-.5,side*1.875-.125],max=[.125,3,side*1.875+.125]),feature='center_support_for_long_market_canopy'))
  mp=HERE/'masters'/f'{key}.json';write(mp,m);t=time.monotonic();c=coordinate_planes.compile_master(m,{'pitch':.25},max_candidate_cells=100000,max_output_cells=40000);assert c['valid'];rd=render_data.make_render_data(c);rp=HERE/'cache'/f'{key}.render.json';write(rp,rd)
  assets[key]=dict(master_path=str(mp.relative_to(ROOT)),master_sha256=sha(mp),render_path=str(rp.relative_to(ROOT)),render_sha256=sha(rp),bounds=rd['bounds'],quad_count=rd['quad_count'],pitch_m=.25)
  report.append(dict(asset=key,candidates=c['candidate_cells'],cells=len(c['cells']),quads=rd['quad_count'],seconds=time.monotonic()-t))
 placements=[fountain];rows=[];rejected=[]
 for idx,p in enumerate(old['placements'][1:]):
  base_yaw=p['yaw_rad'];nx,nz=math.sin(base_yaw),math.cos(base_yaw);members=[]
  for side in (-1,1):
   pos=[p['position_m'][0]+nx*2.25*side,4,p['position_m'][2]+nz*2.25*side];yaw=base_yaw+(math.pi if side<0 else 0);key='timber6' if idx%5==0 else 'cloth8' if idx%4==0 else 'cloth6';poly=bounds_poly(assets[key]['bounds'],pos,yaw)
   reason=None
   if not geo.convex_polygon_contains(site['polygon_xz_m'],poly,1):reason='market edge service reserve'
   elif any(geo.positive_area_overlap(poly,q,0) for q in reserved):reason='public road reserve'
   elif any(math.dist([cx,cz],q)<10 for q in poly) or geo.point_in_convex_polygon([cx,cz],poly):reason='fountain gathering island'
   elif any(geo.positive_area_overlap(poly,q['footprint_xz_m'],0) for q in placements[1:]):reason='other canopy'
   if reason:rejected.append(dict(source=p['id'],side=side,reason=reason));continue
   pid=p['id']+(':south' if side>0 else ':north');function=['grain','cloth_and_housewares','produce','fresh_food'][idx%4];front=[pos[0]+math.sin(yaw)*3.3,pos[2]+math.cos(yaw)*3.3]
   out=dict(id=pid,asset_key=key,position_m=pos,yaw_rad=yaw,scale=[1,1,1],palette_id='market_canvas_'+str(idx%4) if key!='timber6' else 'native_timber',palette_override={'plaster_light':['dfd1ad','c8b78e','b76f50','e8ddc2'][idx%4]} if key!='timber6' else {},footprint_xz_m=poly,function=function,operation_mode='market_day',row_pair_id=p['id']+':pair',customer_front_xz_m=front,minimum_target_customer_lane_m=2.4,finished_floor_y_m=4)
   placements.append(out);members.append(pid)
  if members:rows.append(dict(id=p['id']+':pair',source_anchor=p['position_m'],member_ids=members,rear_gap_m=.5,rear_gap_is_walkway=False,frontage_policy='Back-to-back counters face outward into customer aisles; back gap is not an inferred route.'))
 out=dict(schema='riverstone.registered_market_clusters.r3',status='native_clustering_candidate_pending_walkspace_test_and_view',source_plan_sha256=old['source_plan_sha256'],parent_pack_sha256=sha(oldpath),assets=assets,placements=placements,rows=rows,access_overlay=old['access_overlay'],replace_market_pack=True,replace_landmark_groups=old['replace_landmark_groups'],rejections=rejected,summary=dict(stalls=len(placements)-1,native_cached_assets=len(assets),plaza_area_m2=area(site['polygon_xz_m']),canopy_area_m2=sum(area(p['footprint_xz_m']) for p in placements[1:]),old_canopy_area_m2=12*(len(old['placements'])-1)),limits=['Functional cluster interpretation, not pixel-exact reconstruction of every tent.','Native fountain kept at original4.8m diameter; no scaling or source edit.','No customer/NPC/trading simulation approved.'])
 write(HERE/'resolved_placements.json',out);write(HERE/'compile_report.json',dict(requests=report,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss));print(json.dumps(out['summary']))
if __name__=='__main__':main()
