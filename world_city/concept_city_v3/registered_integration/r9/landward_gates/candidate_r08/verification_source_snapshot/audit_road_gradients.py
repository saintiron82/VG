"""Audit steepest-direction gradient of every final float32 public-road triangle."""
import json,sys,math,numpy as np
from .build_corridors import H,plane,area3,ref
C=H/sys.argv[1];patch=json.load(open(C/'surface_patch.json'));rows=[]
for i in range(0,len(patch['appended_surfaces']['road']),3):
 t=np.asarray(patch['appended_surfaces']['road'][i:i+3],dtype=np.float32).astype(float).tolist();pl=plane(t);rows.append(dict(index=i//3,side='WEST'if t[0][0]<0 else 'EAST',gradient=math.hypot(pl[0],pl[1]),triangle_xyz_m=t,area_m2=area3(t)))
report=dict(scope='Every actual final float32 appended public-road triangle, including full road width and both existing junctions; plane gradient is steepest surface direction, not sparse route grade.',sources=dict(patch=ref(C/'surface_patch.json')),by_side={s:max([r for r in rows if r['side']==s],key=lambda r:r['gradient'])for s in ['WEST','EAST']},count=len(rows),maximum_gradient=max(r['gradient']for r in rows),triangles_above_10_5_percent=sum(r['gradient']>.105 for r in rows));out=C/'actual_road_triangle_gradient_summary.json'
if '--verify'in sys.argv:assert json.load(open(out))==report;print('Exact road-gradient report reproduced')
else:
 with out.open('x')as f:json.dump(report,f,separators=(',',':'));f.write('\n')
