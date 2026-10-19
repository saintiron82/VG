import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
HERE=Path(__file__).resolve().parent
COLORS={'grain':'#bfa16c','produce':'#6f9170','textile':'#b75a4b'}
def draw(pack=None,layout=None,filename='context_plan.png'):
 c=json.load(open(HERE/'source_context.json'));fig,ax=plt.subplots(figsize=(13,10));ax.set_facecolor('#e8dec5')
 ax.add_patch(Polygon(c['site']['polygon_xz_m'],fill=False,ec='#836b49',lw=2))
 for row in c['reservations']:
  ax.add_patch(Polygon(row['polygon'],fc='#d9b36b' if row['kind']=='gathering' else '#d9d3bd',ec='none',alpha=.3))
 for row in c['solids']:
  if row['y_max']>4.04:ax.add_patch(Polygon(row['polygon'],fc='#7b7269',ec='#534b43',lw=.35))
 if not pack:
  from world_city.concept_city_v3.registered_integration.r9.port_market.author import ring
  for p in c['old_stalls']:ax.add_patch(Polygon(ring({'min':[-3,0,-2],'max':[3,4,2]},p),fc='#bdad91',ec='#8c7f69',alpha=.5))
 if pack:
  for p in pack['add_instances']:
   ax.add_patch(Polygon(p['footprint_xz_m'],fc=COLORS[p['trade_family']],ec='#453c31',lw=.65))
   x,y,z=p['position_m'];ax.text(x,z,p['id'].split(':')[-1],fontsize=5,ha='center',va='center')
 if layout:
  for group in layout['clusters']:
   x,z=group['label_xz_m'];ax.text(x,z,group['label'],color='#33281f',fontsize=9,ha='center',fontweight='bold',bbox=dict(facecolor='#fff5db',alpha=.85,edgecolor='none',pad=2))
  for r in layout.get('routes',[]):
   xy=r['path_xz_m'];ax.plot([q[0] for q in xy],[q[1] for q in xy],color='#478ba0' if r['route_type']=='customer' else '#895f9f',lw=.6 if r['route_type']=='customer' else 1.2,alpha=.65)
 for r in c['roads']:
  xy=r['polyline_xz_m'];ax.plot([q[0] for q in xy],[q[1] for q in xy],color='#c39c57',lw=2,alpha=.75)
 f=c['fountain']['position_m'];ax.text(f[0],f[2],'Fountain\n10 m reserve',ha='center',va='center',fontsize=8,color='#675033')
 ax.set_xlim(10,185);ax.set_ylim(116,-24);ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');ax.set_title('Market trade courts | static plan, not a rendered city approval',fontsize=14)
 fig.tight_layout();fig.savefig(HERE/filename,dpi=150);plt.close(fig)
if __name__=='__main__':
 if (HERE/'pack.json').exists():draw(json.load(open(HERE/'pack.json')),json.load(open(HERE/'layout.json')),'candidate_plan.png')
 else:draw()
