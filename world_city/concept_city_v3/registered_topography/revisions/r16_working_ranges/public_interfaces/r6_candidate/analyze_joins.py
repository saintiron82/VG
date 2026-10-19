import sys
sys.dont_write_bytecode=True
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
import study_terminal_profiles as s
import json,math,collections
import numpy as np
SOURCE=json.loads((HERE/'r6_local_source.json').read_text())
s.TRIS=[];s.INDEX=s.a.geo._SpatialIndex(8)
for i,r in enumerate(SOURCE['records']):
 p=[[v[0],v[2]]for v in r['vertices_m']];row=dict(r,local_snapshot_triangle_index=i,polygon_xz_m=p,plane_y_xz_m=list(s.a.affine_plane(r['vertices_m'])));s.TRIS.append(row);s.INDEX.add(i,p)
def draw():
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 fig,ax=plt.subplots(figsize=(12,12));polys=[];colors=[]
 for r in s.TRIS:
  polys.append(r['polygon_xz_m']);g=math.hypot(*r['plane_y_xz_m'][:2]);colors.append(g)
 c=PolyCollection(polys,array=np.array(colors),cmap='turbo',clim=(0,.3),linewidths=.1,edgecolors='#888888');ax.add_collection(c);fig.colorbar(c,ax=ax,label='Actual gradient, capped display at0.3')
 for num,h in enumerate(s.H['terminal_grade_holds']):
  line=np.array(h['polyline_xz_m']);ax.plot(line[:,0],line[:,1],'k-o',markersize=2);e=np.array(s.end_edge(line.tolist(),h['review_width_m']));ax.plot(e[:,0],e[:,1],color='white',linewidth=3);ax.text(*line[-1],str(num),color='white')
 ax.set_xlim(210,228);ax.set_ylim(131,152);ax.set_aspect('equal');ax.grid();fig.savefig(HERE/'source_gradient_map.png',dpi=140)
def scan():
 out=[]
 for num,h in enumerate(s.H['terminal_grade_holds']):
  last=np.array(h['polyline_xz_m'][-1]);direction=np.array(h['polyline_xz_m'][-1])-h['polyline_xz_m'][-2];direction/=np.linalg.norm(direction);perp=np.array([-direction[1],direction[0]]);w=h['review_width_m'];rows=[]
  # Search both along the approach and sideways, preserving exact width.
  for forward in np.arange(-2,5.01,.5):
   for lateral in np.arange(-4,4.01,.5):
    center=last+forward*direction+lateral*perp;e=[(center+sgn*perp*w/2).tolist()for sgn in(-1,1)];p=s.profile(*e)
    if p['grade_violations']or p['incompatible_height_knots']or p['uncovered_t_intervals']or p['overlap_intervals']:continue
    if abs(sum(r['length_m']for r in p['pieces'])-w)>1e-6:continue
    road=sum(r['length_m']for r in p['pieces']if r['source']['material']=='road')
    rows.append(dict(forward_m=float(forward),lateral_m=float(lateral),center_xz_m=center.tolist(),road_width_m=road,max_grade=p['minimum_required_triangle_grade'],profile=p))
  rows.sort(key=lambda r:(-r['road_width_m'],abs(r['forward_m'])+abs(r['lateral_m'])))
  out.append(dict(index=num,candidates=rows[:30]));print(num,'candidates',len(rows),'best',[(r['forward_m'],r['lateral_m'],r['road_width_m'],r['max_grade'])for r in rows[:8]],flush=True)
 (HERE/'moved_join_scan.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':draw();scan()
