import json, pathlib, sys, math
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection,LineCollection
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
HERE=pathlib.Path(__file__).resolve().parent; P=HERE.parents[3]
s=a.load_scene();window=[[90,275],[240,275],[240,390],[90,390]];ix=a.TriangleIndex(s,[window])
fig,ax=plt.subplots(figsize=(14,11))
polys=[];colors=[]
for r in ix.rows:
 plane=r['plane_y_xz_m']; y=[v[1] for v in r['vertices_xyz_m']];polys.append(r['polygon_xz_m']); colors.append('#85bd7b' if max(abs(v-1) for v in y)<1e-6 else '#dfbd7e')
ax.add_collection(PolyCollection(polys,facecolors=colors,edgecolors='none'))
roads=[r['polygon_xz_m']for r in ix.rows if r['material'] in ('road','alley')];ax.add_collection(PolyCollection(roads,facecolors='#77b2d3',edgecolors='none',alpha=.7))
n=json.loads((P/'registered_integration/r8/coverage_plan/native_projection.json').read_text()); retired={r['source_id']for r in json.loads((HERE.parent/'retirement_candidates.json').read_text())['rows']if r.get('matching_level_band_y_m')==1}
for ins in n['instances']:
 ps=ins['native_owner_parts_xz_m']; x,y,z=ins['position_m']
 if 85<x<245 and 270<z<395:
  ax.add_collection(PolyCollection(ps,facecolors='#a80000' if ins['id']not in retired else '#d94edf',edgecolors='black',linewidths=.3,alpha=.6)); ax.text(x,z,ins['id'],fontsize=6)
for m,vs in s['surfaces'].items():
 if m!='bank':continue
 lines=[]
 for j in range(0,len(vs),3):
  t=vs[j:j+3];p=[[v[0],v[2]]for v in t]
  if not a.intersects(a.bounds(p),a.bounds(window)):continue
  if min(v[1] for v in t)<3.2 and max(v[1]for v in t)>1.01:lines.append(p)
 ax.add_collection(PolyCollection(lines,facecolors='none',edgecolors='purple',linewidths=.3))
ax.set_xlim(90,240);ax.set_ylim(390,275);ax.set_aspect('equal');ax.grid();fig.savefig(HERE/'exploration.png',dpi=140)
print('rows',len(ix.rows),'output',HERE/'exploration.png')
