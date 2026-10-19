import sys,json,pathlib,hashlib,math,collections
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r10_density_reservoir import author as a
from world_city.concept_city_v3.registered_topography.revisions.r11_ground_materials import author as b
g=a.geo
bounds=[320,304,336,320]
def area(p):
 if len(p)<3:return 0
 o=p[0];return abs(sum((p[i][0]-o[0])*(p[i+1][1]-o[1])-(p[i][1]-o[1])*(p[i+1][0]-o[0]) for i in range(1,len(p)-1)))/2
def tidy(p):
 out=[]
 for q in p:
  if not out or math.dist(q,out[-1])>1e-12:out.append(q)
 if len(out)>1 and math.dist(out[0],out[-1])<=1e-12:out.pop()
 return out
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report={'bounds':bounds,'inputs':{},'versions':{}}
for label,m in [('r09',a.prior),('r10',a),('r11',b)]:
 rs=m.surface_domains(bounds,False);hits=[]
 for i,r in enumerate(rs):
  for j in range(i+1,len(rs)):
   s=rs[j];q=g.convex_intersection(tidy(r['polygon_xz_m']),tidy(s['polygon_xz_m']));v=area(q)
   if v>1e-7:hits.append(dict(area_m2=v,polygon_xz_m=q,left_index=i,right_index=j,left=r,right=s))
 report['inputs'][m.__file__]=sha(pathlib.Path(m.__file__))
 report['versions'][label]={'records':len(rs),'area_m2':sum(area(r['polygon_xz_m']) for r in rs),'overlaps':hits,'pairwise_overlap_m2':sum(h['area_m2'] for h in hits)}
 print(label,len(rs),report['versions'][label]['area_m2'],len(hits),report['versions'][label]['pairwise_overlap_m2'],flush=True)
(H/'partition_failure_320_304.json').write_text(json.dumps(report,indent=2)+'\n')
