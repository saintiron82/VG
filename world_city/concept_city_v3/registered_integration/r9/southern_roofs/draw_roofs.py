"""Exact cached native geometry; software sheet, not composed runtime approval."""
from .author_roofs import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def run():
 scene=load(BASE);pack=load(HERE/'pack.json');fig=plt.figure(figsize=(18,14),facecolor='#eeeade');families=['bank_joinery','bank_loft_store','bank_craft_lodging','market_lodging'];light=np.array([-.6,1,.6]);light/=np.linalg.norm(light)
 for row,f in enumerate(families):
  source='working_r01_'+f;sample=next(p for p in scene['common_instances']if p['asset_key']==source)
  for col,key in enumerate([source,'r9_south_'+f+'_a','r9_south_'+f+'_b']):
   a=scene['common_assets'].get(key,pack['common_assets'].get(key));r=load(ROOT/a['render_path']);ax=fig.add_subplot(4,3,row*3+col+1,projection='3d');ax.set_facecolor('#eeeade');materials=dict(r['materials']);materials.update(sample['palette_override']);polys=[];colors=[]
   for g in r['groups']:
    raw=materials[g['material']];color=raw.get('color',raw.get('albedo','#888888'))if isinstance(raw,dict)else raw;color=color.lstrip('#');rgb=np.array([int(color[k:k+2],16)/255 for k in (0,2,4)])
    for q in g['quads']:
     v=np.array(q);n=np.cross(v[1]-v[0],v[2]-v[1]);n/=np.linalg.norm(n);shade=.68+.32*max(0,np.dot(n,light));polys.append([[v[0],v[2],v[1]]for v in q]);colors.append(tuple(rgb*shade))
   ax.add_collection3d(Poly3DCollection(polys,facecolors=colors,edgecolors='none',linewidths=0,zsort='average'));b=r['bounds'];ax.set_xlim(-16,16);ax.set_ylim(-6,6);ax.set_zlim(0,12);ax.set_box_aspect((32,12,12));ax.view_init(elev=34,azim=58);ax.set_axis_off();ax.set_title(f.replace('_',' ')+' | '+['original','west group A','east group B'][col],fontsize=10,pad=-10)
 fig.suptitle('Southern working ranges | original vs eight shared native roof/storey variants',fontsize=18,y=.97);fig.text(.06,.03,'Exact common cached quads; unchanged original palettes. Every native cell below 2.5 m and every entrance is identical.\n30 retained placements; all new bounds contained by the original envelopes. Software sheet only; actual composed city review pending.',fontsize=11);fig.subplots_adjust(wspace=0,hspace=0);fig.savefig(HERE/'native_roof_comparison.png',dpi=125,bbox_inches='tight');plt.close(fig)
if __name__=='__main__':run()
