import json,collections,math
from . import author as a

def run():
 groups=collections.defaultdict(list)
 for r in a.OWNERS:
  if r['kind']=='r14_precinct_native_hole':groups[r['source_placement_id']].append(r)
  elif r['kind']=='r14_merchant_native_hole':groups[r['property_id']].append(r)
 results=[]
 for gid,expected in groups.items():
  pts=[p for r in expected for p in r['polygon_xz_m']];b=[min(p[0] for p in pts)-.1,min(p[1] for p in pts)-.1,max(p[0] for p in pts)+.1,max(p[1] for p in pts)+.1]
  rs=a.surface_domains(b,False);actual=[r for r in rs if r.get('source_placement_id')==gid or(r['kind']=='r14_merchant_native_hole' and r.get('property_id')==gid)]
  want=sum(a.geo.polygon_area(r['polygon_xz_m']) for r in expected);got=sum(a.geo.polygon_area(r['polygon_xz_m']) for r in actual)
  area=sum(a.geo.polygon_area(r['polygon_xz_m']) for r in rs);box=(b[2]-b[0])*(b[3]-b[1]);idx=a.geo._SpatialIndex(16);overlaps=[]
  for i,r in enumerate(rs):
   p=a.clean(r['polygon_xz_m'])
   for j in idx.candidates(p):
    q=a.clean(a.geo.convex_intersection(p,a.clean(rs[j]['polygon_xz_m'])))
    if q and a.geo.polygon_area(q)>1e-7:overlaps.append(dict(left=r['owner_id'],right=rs[j]['owner_id'],area_m2=a.geo.polygon_area(q)))
   idx.add(i,p)
  result=dict(id=gid,bounds_xz_m=b,expected_native_area_m2=want,masked_native_area_m2=got,missing_native_mask_area_m2=want-got,partition_area_delta_m2=area-box,partition_records=len(rs),positive_overlaps=overlaps)
  results.append(result);print(gid,'maskdelta',want-got,'partdelta',area-box,'overlaps',len(overlaps),flush=True)
 out=dict(schema='riverstone.r14_native_ownership_audit.v1',author_sha256=a.R04.sha(a.HERE/'author.py'),groups=results)
 (a.HERE/'ownership_audit_repaired.json').write_text(json.dumps(out,indent=2)+'\n');return out
if __name__=='__main__':run()
