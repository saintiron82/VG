from .check_candidates import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
fig,ax=plt.subplots(figsize=(13,8))
for i in s['common_instances']:
 x,y,z=i['position_m']
 if not(-430<x<-240 and -280<z<-110):continue
 r=json.load(open(ROOT/s['common_assets'][i['asset_key']]['render_path']))
 if i['id']=='TRAIN:r09:coarse':
  for group in r['groups']:
   for q in group['quads']:
    q=[transform(v,i)for v in q]
    if min(v[1]for v in q)>17.9 and max(v[1]for v in q)<18.01:ax.add_patch(Polygon([[v[0],v[2]]for v in q],color='#eee5bb'))
 else:
  b=bs[i['asset_key']];p=[transform([xx,0,zz],i)for xx,zz in [(b['min'][0],b['min'][2]),(b['max'][0],b['min'][2]),(b['max'][0],b['max'][2]),(b['min'][0],b['max'][2])]]
  ax.add_patch(Polygon([[v[0],v[2]]for v in p],color='#72857a',alpha=.5))
  if ':FOOTING'not in i['id']:ax.text(x,z,i['id'].replace('FORT_CURTAIN_','W').replace('castle_registered:','C:'),fontsize=5)
p=json.load(open(ROOT/'world_city/concept_city_v3/registered_source/plan.json'));r=next(r for r in p['roads']if r['id']=='CASTLE_APPROACH');pts=r['polyline_xz_m'];ax.plot(*zip(*pts),color='red')
ax.set_xlim(-430,-235);ax.set_ylim(-115,-285);ax.set_aspect('equal');ax.grid();fig.savefig(H/'training_ownership_plan.png',dpi=150)
