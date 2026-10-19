"""Read-only coverage of requested frontages by the current finite R18 domain."""
import json,math
from . import public_domain as d
from ..r17_district_batches.audit_retired_boundaries import interval
from ..r17_district_batches import author as a
from .survey import HERE,ROAD_IDS
PATH=a.CITY/'registered_topography/revisions/r17_district_batches/contour_bulk_r01/public_interface_requests.json'
EXPECTED='75838459adef3a81f7078dd8bad5b068ad6533e6ce72a71b445fb145b118a33f'
def run():
 assert a.sha(PATH)==EXPECTED;request=json.loads(PATH.read_bytes());polys=d.polygons();ix=a.geo._SpatialIndex(8)
 for i,p in enumerate(polys):ix.add(i,p)
 rows=[]
 for r in request['entries']:
  p,q=r['requested_public_edge_xz_m'];spans=sorted(s for i in ix.candidates([p,q])if(s:=interval(p,q,polys[i])));merged=[]
  for lo,hi in spans:
   if merged and lo<=merged[-1][1]+1e-9:merged[-1][1]=max(hi,merged[-1][1])
   else:merged.append([lo,hi])
  length=math.dist(p,q);covered=sum(hi-lo for lo,hi in merged)*length
  rows.append(dict(holding_id=r['holding_id'],public_road_id=r['public_road_id'],road_id_in_primary16=r['public_road_id']in ROAD_IDS,edge_xz_m=[p,q],width_m=length,current_domain_covered_length_m=covered,uncovered_length_m=length-covered,covered_t_intervals=merged,status='IN_CURRENT_FINITE_DOMAIN_PROFILE_PENDING'if length-covered<=1e-7 else'NEEDS_FINITE_DOMAIN_OR_EXACT_BOUNDARY_REVIEW'))
 out=dict(request=dict(path=str(PATH.relative_to(a.ROOT)),sha256=EXPECTED),domain_source_refs=d.source_refs(),rows=rows,scope='This is finite domain coverage only; no old corner height was made fixed and no requested approach is accepted.')
 (HERE/'contour_domain_screen.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print('covered',sum(r['uncovered_length_m']<=1e-7 for r in rows),'held',sum(r['uncovered_length_m']>1e-7 for r in rows));print([(r['holding_id'],r['public_road_id'],r['uncovered_length_m'])for r in rows if r['uncovered_length_m']>1e-7])
if __name__=='__main__':run()
