"""Bounded north-end gate shift for the retained craft U court."""
from . import geometry as g
from .refit_held_private_entries import PublicField,route_intervals,rows
from .activate_backlands_subset import MaskIndex
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import public_domain
import math,copy
OUT=g.HERE/'b08_north_gate_refit_r01'
LAYOUT=a.HERE/'coherent_batch20_r01/effective_source_layout_r03.json'
FIELD=g.CITY/'registered_topography/revisions/public_corridors_r18/finite_field_candidate_r04_common.json'
def run():
 OUT.mkdir(exist_ok=True);layout=g.load(LAYOUT);h=next(h for h in layout['holdings']if h['id']=='BLOCK_008:R8_C003');mf=g.load(g.HERE/'effective_city_manifest_r01.json');own=[p for p in mf['placements']if p.get('holding_id')==h['id']];p=next(p for p in own if ':FABRIC:'in p['id']);center=p['position_m'][::2];yaw=p['yaw_rad'];oldgate=h['gate_position_xz_m'];cc,ss=math.cos(yaw),math.sin(yaw);d=[oldgate[i]-center[i]for i in range(2)];localz=ss*d[0]+cc*d[1];field=PublicField(g.load(FIELD)['records']);pub=MaskIndex(public_domain.records());court=MaskIndex([dict(id=h['id'],polygon_xz_m=h['holding_polygon_xz_m'])]);native=MaskIndex([dict(id=p['id'],polygon_xz_m=q)for p in own for q in p['native_walking_obstacles_xz_m']]);others=MaskIndex([dict(id=x['id'],polygon_xz_m=x['holding_polygon_xz_m'])for x in layout['holdings']if x['id']!=h['id']]);candidates=[];diag=[]
 for lx in [-8,-9,-10,-11,-12,-13,-14]:
  gate=g.xform([lx,localz],center,yaw);link=[oldgate,gate];ilps=g.ribbons(link,2.);ih=native.hit(ilps)
  if any(':FABRIC:'in x['id']for x in ih):diag.append(dict(local_x=lx,error='internal_native',hits=ih));continue
  for target in [[94,-29],[94,-28],[94,-27],[95,-28],[95,-27],[96,-27],[96,-26],[97,-26],[98,-25],[98.5,-24.5]]:
   ev=field.at(target)
   if not ev:continue
   line=[gate,target];ps=g.ribbons(line,2.);hits=native.hit(ps);other=others.hit(ps);fixed=field.intersection(ps);pi=route_intervals(line,2.,pub);ci=route_intervals(line,2.,court);first=min((x['station_range_m'][0]for x in pi),default=999);last=max((x['station_range_m'][1]for x in ci),default=0.);rise=max((abs(a.common.height(t['plane_y_xz_m'],v)-h['floor_y_m'])for t in fixed for v in t['polygon_xz_m']),default=999);run=first-last;screen=rise/run if run>0 else 999;rr=dict(local_x=lx,gate=gate,target=target,target_y=ev['y_m'],first=first,last=last,run=run,rise=rise,screen=screen,native=hits,other=other);diag.append(rr)
   if any(':FABRIC:'in x['id']for x in hits)or other or not fixed or screen>.2:continue
   candidates.append(dict(holding_id=h['id'],candidate_index=len(candidates),floor_y_m=h['floor_y_m'],original_floor_y_m=h['floor_y_m'],proposed_rigid_y_delta_m=0.,width_m=2.,original_gate_xz_m=oldgate,gate_xz_m=gate,gate_point_xz_m=gate,gate_changed=True,internal_court_link_xz_m=link,internal_court_link_polygons_xz_m=ilps,polyline_xz_m=line,polygons_xz_m=ps,public_road_id=h['public_road_id'],public_segment=None,public_target_evidence=ev,fixed_public_regions=fixed,first_full_width_public_station_m=first,last_fixed_holding_station_m=last,strict_private_rise_length_m=run,source_average_rise_screen=screen,native_boundary_contacts=hits+ih,additional_retirement_ids=[],required_core_floor_interval_m=[2.27737236,4.66958401],source_layout=g.ref(LAYOUT),public_field=g.ref(FIELD),status='BOUNDED_GATE_SHIFT_PENDING_FINITE_PUBLIC_PROFILE'))
 g.write(OUT/'source_candidates.json',dict(holding_id=h['id'],source_layout=g.ref(LAYOUT),source_public_field=g.ref(FIELD),author=g.ref(__file__),candidates=candidates,diagnostic=diag,activation=False));print(g.ref(OUT/'source_candidates.json'));print('good',len(candidates));print([{k:v for k,v in c.items()if k in ['candidate_index','gate_xz_m','public_target_evidence','strict_private_rise_length_m','source_average_rise_screen']}for c in candidates[:8]])
if __name__=='__main__':run()
