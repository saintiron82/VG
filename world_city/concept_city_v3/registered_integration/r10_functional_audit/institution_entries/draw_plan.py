import os
os.environ['MPLCONFIGDIR']='/tmp/r10-institution-mpl';os.environ['XDG_CACHE_HOME']='/tmp/r10-institution-cache'
from build_candidate import *
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
D=read(H/'context.json')['sites']['abbey'];R=read(H/'candidate_r01/routes.json');P=read(H/'candidate_r01/surface_patch.json');old=Ground(D['surface_rows'])
fig,(ax,bx)=plt.subplots(2,1,figsize=(13,9),height_ratios=[3,1]);ax.set_title('Abbey public arrival and admitted-patient route | source geometry diagram')
for r in D['surface_rows']:
 if r['material']=='road':ax.add_patch(Polygon([xz(v)for v in r['triangle']],color='#bfaa8b',alpha=.6))
for r in D['floors']:ax.add_patch(Polygon(r['polygon_xz_m'],color='#c8c8c2',alpha=.5))
for r in P['ownership'][0]['ownership_polygons_xz_m']:ax.add_patch(Polygon(r,color='#a2d9cb',alpha=.5))
for r in D['bodies']:ax.add_patch(Polygon(r['polygon_xz_m'],color='#41463f'))
for r,col in zip(R['routes'],['#568bb2','#008b6b','#de7d24']):
 pts=r['points'];ax.plot([v[0]for v in pts],[v[2]for v in pts],color=col,lw=2.4,label=r['id'].replace('R10_ABBEY_',''))
for i in read(H/'candidate_r01/pack.json')['add_instances']:ax.plot(i['position_m'][0],i['position_m'][2],'s',color='#775037',ms=5)
ax.text(-333,-4,'Private herb garden\nExisting wall retained',fontsize=9,ha='center');ax.text(-325,-24.5,'Existing infirmary',fontsize=10,ha='center');ax.annotate('Admission boundary',[-259,-7.8236],[-267,14],arrowprops={'arrowstyle':'->'},fontsize=9);ax.annotate('16 m² waiting pocket',[-255,-3.5],[-247,9],arrowprops={'arrowstyle':'->'},fontsize=9)
ax.set(xlim=(-340,-237),ylim=(19,-30),xlabel='World X (m)',ylabel='World Z (m)');ax.set_aspect('equal');ax.legend(loc='upper right',fontsize=8);ax.grid(alpha=.2)
r=next(x for x in R['routes']if x['id']=='R10_ABBEY_PUBLIC_ROAD_TO_ADMISSION');pts=r['points'];dist=[0]
for a,b in zip(pts,pts[1:]):dist.append(dist[-1]+math.dist(xz(a),xz(b)))
bx.plot(dist,[old.at(xz(v))for v in pts],label='Before: original finite surface',color='#b4534b');bx.plot(dist,[v[1]for v in pts],label='After: bounded arrival ramp',color='#008b6b');bx.set(xlabel='Distance from public road (m)',ylabel='Support Y (m)',title='Same ~0.25 m stations: original 0.488 m lip removed');bx.legend(fontsize=9);bx.grid(alpha=.2);fig.tight_layout();fig.savefig(H/'candidate_plan.png',dpi=150)
