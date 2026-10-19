from .. import author as a
from ..incident_risers_r01.solve import index

def audit(domains,triangles):
 tops=[t['polygon_xz_m']for t in triangles];ti=index([dict(polygon_xz_m=p)for p in tops]);di=index([dict(polygon_xz_m=p)for p in domains]);gap=0.;outside=0.;overlap=0.
 for p in domains:
  gap+=sum(a.geo.polygon_area(q)for q in a.common.subtract([p],[tops[i]for i in sorted(ti.candidates(p))]))
 for i,p in enumerate(tops):
  outside+=sum(a.geo.polygon_area(q)for q in a.common.subtract([p],[domains[j]for j in sorted(di.candidates(p))]))
  for j in ti.candidates(p):
   if j>i:overlap+=a.geo.polygon_area(a.clip(p,tops[j])or[])
 return dict(domain_area_m2=sum(a.geo.polygon_area(p)for p in domains),missing_area_m2=gap,outside_area_m2=outside,positive_overlap_area_m2=overlap)
