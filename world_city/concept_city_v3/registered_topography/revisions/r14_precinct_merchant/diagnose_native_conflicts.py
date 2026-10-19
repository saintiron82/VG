import json,collections
from . import author as a
out=[]
for gid in ['CLERGY_CANONS_CLOSE','CLERGY_SCHOOL_SERVICE','ABBEY_NORTH_WORK']:
 expected=[r for r in a.OWNERS if r.get('source_placement_id')==gid];pts=[p for r in expected for p in r['polygon_xz_m']];b=[min(p[0] for p in pts)-.1,min(p[1] for p in pts)-.1,max(p[0] for p in pts)+.1,max(p[1] for p in pts)+.1];rs=a.surface_domains(b,False);idx=a.geo._SpatialIndex(16)
 for i,r in enumerate(rs):idx.add(i,r['polygon_xz_m'])
 for f in expected:
  for i in idx.candidates(f['polygon_xz_m']):
   r=rs[i]
   if r.get('source_placement_id')==gid:continue
   p=a.clean(a.geo.convex_intersection(f['polygon_xz_m'],a.clean(r['polygon_xz_m'])))
   if p:out.append(dict(placement_id=gid,bearing_id=f['owner_id'],preserved_owner_id=r['owner_id'],preserved_kind=r['kind'],polygon_xz_m=p,area_m2=a.geo.polygon_area(p),native_floor_y_m=f['floor_y_m'],preserved_owner=r))
summary=collections.Counter()
for r in out:summary[(r['placement_id'],r['preserved_owner_id'],r['preserved_kind'])]+=r['area_m2']
print(summary)
(a.HERE/'native_conflicts.json').write_text(json.dumps(out,indent=2)+'\n')
