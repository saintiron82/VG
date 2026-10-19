import json,math
from .height_field import HERE
from . import finite_geometry_r03 as g
from .classify_unknown_edges_r01 import ref
from ..r17_district_batches import author as a

def main():
 op=HERE/'north_mask_restoration_r01.json';np=HERE/'north_connected_earth_r03_candidate.json';rp=HERE/'joint_boundary_north_rebound_final_r01.json';hp=HERE/'local_completion_handoff_final_r01.json';old=json.loads(op.read_bytes())['physical_earth_owners'];new=json.loads(np.read_bytes())['physical_earth_owners'];rebound=json.loads(rp.read_bytes());handoff=json.loads(hp.read_bytes());idx=a.geo._SpatialIndex(4)
 for i,r in enumerate(new):idx.add(i,r['polygon_xz_m'])
 rows=[];maxdy=0
 for r in old:
  p=r['polygon_xz_m'];hits=[];remaining=[p]
  for i in idx.candidates(p):
   n=new[i];q=g.clip(p,n['polygon_xz_m']);ar=g.area(q)
   if ar<=1e-14:continue
   dy=max(abs(a.common.height(r['plane_y_xz_m'],v)-a.common.height(n['plane_y_xz_m'],v))for v in q);maxdy=max(maxdy,dy);hits.append(dict(new_owner_id=n['id'],overlap_polygon_xz_m=q,area_m2=ar,maximum_replaced_top_height_delta_m=dy));remaining=g.subtract(remaining,[n['polygon_xz_m']])
  rows.append(dict(old_owner_id=r['id'],old_area_m2=g.area(p),covered_by_new_area_m2=math.fsum(x['area_m2']for x in hits),uncovered_polygons_xz_m=remaining,uncovered_area_m2=math.fsum(g.area(q)for q in remaining),pieces=hits))
 area=math.fsum(r['old_area_m2']for r in rows);uncovered=math.fsum(r['uncovered_area_m2']for r in rows);assert uncovered<1e-9
 assert rebound['appended_surfaces']['ground_earth']==[]
 retired={r['id']for r in old};assert retired==set(handoff['retire_physical_owner_ids']);assert len([r for r in rebound['north_retirement_ledger']if r['material']=='ground_earth'])==16
 out=dict(schema='riverstone.r18.north_atomic_replacement_review.v1',status='PASS_ATOMIC_REPLACEMENT_WITH_NO_RETAINED_OLD_TOPS',sources=[ref(op),ref(np),ref(rp),ref(hp)],operation='REPLACE_OLD_EIGHT_OWNERS_AND_16_TOP_TRIANGLES_THEN_APPEND_NEW_COMPONENT',old_owner_count=8,old_triangle_count=16,old_area_m2=area,new_component_area_m2=29.330924142128385,old_new_geometric_overlap_m2=math.fsum(r['covered_by_new_area_m2']for r in rows),old_uncovered_by_new_area_m2=uncovered,retained_old_owner_count=0,retained_old_triangle_count=0,final_new_vs_retained_old_overlap_m2=0,net_new_earth_area_m2=29.330924142128385-area,maximum_old_replaced_earth_height_delta_m=maxdy,rows=rows,limits=['Old/new candidate domains intentionally overlap; simultaneous activation is forbidden.','Zero final overlap follows exact source-index/hash retirement of all16 old triangles, not a claim that the candidate polygon sets are disjoint.','R07 road tops remain untouched; replaced earth is outside canonical traffic.'])
 p=HERE/'north_atomic_replacement_review_r01.json';p.write_text(json.dumps(out,separators=(',',':'))+'\n');print(ref(p));print({k:v for k,v in out.items()if k not in ['sources','rows','limits']})
if __name__=='__main__':main()
