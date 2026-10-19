import json,collections,math
from .audit import HERE,ny
from .. import author as a
from ..final_profile_audit_r01 import exact_clip as e

def area(p):return abs(sum((p[i][0]-p[0][0])*(p[i+1][1]-p[0][1])-(p[i][1]-p[0][1])*(p[i+1][0]-p[0][0])for i in range(1,len(p)-1)))/2 if len(p)>2 else 0

def run():
 h=json.loads((HERE.parent/'coherent_final24_r02/physical_owner_handoff_r03.json').read_bytes());report=json.loads((HERE/'report.json').read_bytes());rows=[]
 lists=[('native',h['native_holes']),('public',h['public_fixed_regions']),('new_top',h['rendered_plane_owners'])];idxs=[]
 for kind,rs in lists:
  ix=a.geo._SpatialIndex(2)
  for i,r in enumerate(rs):ix.add(i,r['polygon_xz_m'])
  idxs.append((kind,rs,ix))
 for case in report['cases']:
  if case['float32_normal_y']>=0:continue
  p=[[v[0],v[2]]for v in case['vertices_xyz_m']];hits=[]
  for kind,rs,ix in idxs:
   for i in ix.candidates(p):
    r=rs[i];q=e.clip(p,r['polygon_xz_m']);ar=area(q)
    if ar>0:hits.append(dict(kind=kind,index=i,id=r.get('id'),area_m2=ar,ratio=ar/(case['source_normal_y']/2),polygon_xz_m=q))
  hits=sorted(hits,key=lambda r:-r['area_m2']);rows.append(dict(source_case=case,intersections=hits));print(case.get('appended_triangle_index',case.get('source_triangle_index')),[(r['kind'],r['id'],r['ratio'])for r in hits[:12]],flush=True)
 (HERE/'ownership_classification.json').write_text(json.dumps(dict(records=rows),separators=(',',':'))+'\n')
if __name__=='__main__':run()
