from prepare import *
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
p=load(HERE/'preflight.json');source=load(CITY/'registered_source/plan.json');fig,axes=plt.subplots(1,3,figsize=(17,8),layout='constrained');titles=['Estate rear grounds','Cathedral productive grounds','Abbey working gardens'];sites=[['B03_ESTATE'],['C_'],['A_']];colors=['#8caa65','#a2ad66','#6b8e56','#b4a47a','#9f9b61','#78924e']
for ax,prefixes,title in zip(axes,sites,titles):
 selected=[h for h in p['holdings']if any(h['id'].startswith(k)for k in prefixes)];ps=[v for h in selected for poly in h['polygon_parts_xz_m']for v in poly];x0,z0,x1,z1=min(p[0]for p in ps)-15,min(p[1]for p in ps)-15,max(p[0]for p in ps)+15,max(p[1]for p in ps)+15
 for s in source['spaces']:
  ax.add_collection(PolyCollection([s['polygon_xz_m']],facecolors='#e7e4d6',edgecolors='#c4c0b6',linewidths=.4))
 for road in source['roads']:
  ax.plot(*zip(*road['polyline_xz_m']),color='#9d8f7c',lw=2)
 for h in selected:
  color=colors[p['holdings'].index(h)];ax.add_collection(PolyCollection(h['polygon_parts_xz_m'],facecolors=color,edgecolors='none',alpha=.75));ax.add_collection(PolyCollection([w['polygon_xz_m']for w in h['boundary_spans']],facecolors='#625844',edgecolors='none'));ax.plot(*zip(*h['source_access']['polyline_xz_m']),color='#a94638',lw=1.5)
  ax.add_collection(PolyCollection([v['footprint_xz_m']for v in h['plantings']],facecolors='#245432'if 'orchard'in h['function']else'#68513d',edgecolors='none'))
  ax.scatter(*h['opening_center_xz_m'],s=35,c='#f8ecae',edgecolors='#a94638',zorder=8);cx,cz=h['centroid_xz_m'];ax.text(cx,cz,h['id'].replace(':1','')+'\n'+f"{h['area_m2']:,.0f} m²",fontsize=7,ha='center',va='center',bbox=dict(facecolor='white',alpha=.8,edgecolor='none',pad=2))
 ax.set_xlim(x0,x1);ax.set_ylim(z1,z0);ax.set_aspect('equal');ax.set_title(title);ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');ax.grid(alpha=.12)
fig.suptitle('Productive ground phase 01 | 6 holdings, 16,809.75 m²\nFinite source fields and native boundary preflight; red access profiles remain under review',fontsize=13);fig.savefig(HERE/'phase01_plan.png',dpi=130)
