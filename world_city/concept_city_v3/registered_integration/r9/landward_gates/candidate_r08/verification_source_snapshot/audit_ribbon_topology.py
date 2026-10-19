"""Audit final float32 road vertices and authored cross-sections, not route metadata."""
import json,sys,math,collections,numpy as np
from pathlib import Path
from .build_corridors import H,ref,xz,plane,area3
from world_city.runtime_city.checks import placement as geo
C=H/sys.argv[1];p=json.load(open(C/'surface_patch.json'));groups=collections.defaultdict(lambda:collections.defaultdict(list));steep=[]
for i,v in enumerate(p['appended_surfaces']['road']):
 q=np.asarray(v,dtype=np.float32).tolist();groups[(q[0],q[2])][q[1]].append(i//3)
conflicts=[dict(xz_m=list(q),height_variants=[dict(y_m=y,triangle_indices=sorted(set(ids)))for y,ids in ys.items()],max_delta_m=max(ys)-min(ys))for q,ys in groups.items()if len(ys)>1]
for i in range(0,len(p['appended_surfaces']['road']),3):
 t=np.asarray(p['appended_surfaces']['road'][i:i+3],dtype=np.float32).astype(float).tolist()
 try:pl=plane(t)
 except ZeroDivisionError:continue
 grade=math.hypot(pl[0],pl[1])
 if grade>.105:steep.append(dict(triangle_index=i//3,grade=grade,area_m2=area3(t),triangle_xyz_m=t))
folds=[]
for owner in p['ownership']:
 sections=owner.get('shared_cross_sections_xyz_m',[])
 for i,(a,b)in enumerate(zip(sections,sections[1:])):
  t=[a[1],a[2],b[2],b[1]];q=[xz(v)for v in t];signs=[]
  for aa,bb,cc in zip(q,q[1:]+q[:1],q[2:]+q[:2]):signs.append((bb[0]-aa[0])*(cc[1]-bb[1])-(bb[1]-aa[1])*(cc[0]-bb[0]))
  if min(signs)<-1e-8 and max(signs)>1e-8:folds.append(dict(owner=owner['id'],section=i,height_range_m=max(v[1]for v in t)-min(v[1]for v in t),corners_xyz_m=t))
report=dict(scope='Only appended public-road top under the single-height corridor/junction ownership contract; native bridge and retained lower bank are separate domains and excluded.',sources=dict(patch=ref(C/'surface_patch.json'),audit=ref(Path(__file__))),float32_xz_height_conflicts=conflicts,conflicts_over_0_1mm=[r for r in conflicts if r['max_delta_m']>.0001],nonconvex_section_quads=folds,nonlevel_nonconvex_section_quads=[r for r in folds if r['height_range_m']>.0001],float32_road_triangles_over_10_5_percent=sorted(steep,key=lambda r:r['grade'],reverse=True))
report['status']='PASS'if not conflicts and not report['nonlevel_nonconvex_section_quads'] and max([r['grade']for r in steep]or[0])<=.1051 else 'FAIL'
(C/'float32_ribbon_topology_audit.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print(json.dumps(dict(conflicts=len(conflicts),conflicts_over_0_1mm=len(report['conflicts_over_0_1mm']),nonlevel_folded_quads=len(report['nonlevel_nonconvex_section_quads']),steep_triangles=len(steep),steep_area_m2=sum(r['area_m2']for r in steep),max_grade=max([r['grade']for r in steep]or[0]))))
