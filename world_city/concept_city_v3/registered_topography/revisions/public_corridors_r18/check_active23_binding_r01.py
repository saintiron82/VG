"""Bind final common candidate to the exact active23 physical-owner handoff."""
import json,math
from .height_field import HERE
from . import finite_geometry_r03 as g
from ..r17_district_batches import author as a

def main():
 p=HERE/'finite_field_candidate_r04_common.json';h=a.HERE/'contour_bulk_r01/physical_owner_handoff_r02.json';d=json.loads(p.read_bytes());hand=json.loads(h.read_bytes());ix=a.geo._SpatialIndex(4)
 for i,r in enumerate(d['records']):ix.add(i,r['polygon_xz_m'])
 tests=0;error=0.;bad=[]
 for r in hand['public_fixed_regions']:
  for i in ix.candidates(r['polygon_xz_m']):
   s=d['records'][i];q=g.clip(r['polygon_xz_m'],s['polygon_xz_m'])
   if not q:continue
   tests+=1;e=max(abs(a.common.height(r['plane_y_xz_m'],v)-a.common.height(s['plane_y_xz_m'],v))for v in q);error=max(error,e)
   if e>1e-7:bad.append(dict(fixed_id=r['id'],owner_id=s['id'],error_m=e,polygon_xz_m=q))
 previous=json.loads((HERE/'released_frontage_parity_r02.json').read_bytes());affected={r['holding_id']for r in previous['failures']};active=set(hand['accepted_holding_ids']);affected_active=sorted(affected&active)
 out=dict(status='PASS_ACTIVE23_FIXED_PUBLIC_PLANES'if not(bad or affected_active)else'HELD_ACTIVE23_BINDING',candidate=dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p)),physical_owner_handoff=dict(path=str(h.relative_to(a.ROOT)),sha256=a.sha(h)),active_holding_ids=sorted(active),fixed_region_count=len(hand['public_fixed_regions']),intersections=tests,maximum_plane_difference_m=error,failures=bad,affected_active_holding_ids=affected_active,held_frontage_dependencies=sorted(affected-active),earlier_released_parity_report_sha256=a.sha(HERE/'released_frontage_parity_r02.json'),code_sha256=a.sha(__file__),scope='Finite intersection plane parity for the frozen active23 only. Held B006 C001 and B008 C003 remain unpromoted. Side closure and controller replay pending.')
 (HERE/'active23_public_binding_review_r01.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print(out)
if __name__=='__main__':main()
