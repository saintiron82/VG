"""Software inspection of exact compiled quads, not a city render."""
from .design import *
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/district-fabric-mpl')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def run():
 report=load(HERE/'compile_report.json');scene=load(R7);palettes={i['palette_id']:i.get('palette_override',{})for i in scene['common_instances']if i['source_pack']=='working_ranges_r01'}
 fig=plt.figure(figsize=(15,7),facecolor='#ece9df')
 for i,(key,f)in enumerate(FAMILIES.items()):
  a=report['assets']['district_r01_'+key];r=load(ROOT/a['render_path']);ax=fig.add_subplot(1,3,i+1,projection='3d');ax.set_facecolor('#ece9df');polys=[];colors=[];mats=copy.deepcopy(r['materials']);mats.update(palettes[f['palette']]);light=np.array([-.6,1,.6]);light/=np.linalg.norm(light)
  for g in r['groups']:
   raw=mats[g['material']];color=raw.get('color',raw.get('albedo','#888888'))if isinstance(raw,dict)else raw;color=color.lstrip('#');rgb=np.array([int(color[k:k+2],16)/255 for k in(0,2,4)])
   for q in g['quads']:
    v=np.array(q);n=np.cross(v[1]-v[0],v[2]-v[1]);n/=np.linalg.norm(n);polys.append([[v[0],v[2],v[1]]for v in q]);colors.append(tuple(rgb*(.70+.30*max(0,np.dot(n,light)))))
  ax.add_collection3d(Poly3DCollection(polys,facecolors=colors,edgecolors='none',linewidths=0,zsort='average'));b=r['bounds'];ax.set_xlim(b['min'][0]-1,b['max'][0]+1);ax.set_ylim(b['min'][2]-1,b['max'][2]+1);ax.set_zlim(0,b['max'][1]+.5);ax.set_box_aspect((b['max'][0]-b['min'][0],b['max'][2]-b['min'][2],b['max'][1]));ax.view_init(elev=35,azim=60);ax.set_axis_off();ax.set_title(key.replace('_',' ')+'\n'+str(a['quad_count'])+' native quads',fontsize=13)
 fig.suptitle('R8 district fabric | attached ranges and actual open courts',fontsize=20);fig.text(.08,.08,'Exact native common meshes. Approved clay, wood and slate semantic palette bindings preserved.\nNo whole-house scaling, edited occupancy cells or new mesh engine. Openings are real closed leaves; no interior traversal claim.',fontsize=11);fig.savefig(HERE/'native_family_review.png',dpi=160,bbox_inches='tight');plt.close(fig)
if __name__=='__main__':run()
