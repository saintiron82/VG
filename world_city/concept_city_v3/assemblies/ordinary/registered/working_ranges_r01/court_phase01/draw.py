"""Software-native court inspection: exact quads and exact route masks, no GUI."""
from .author import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
LABELS={'DOMESTIC_BOUNDARY':'Low enclosure','DOMESTIC_DRYING_FRAME':'Drying frame','DOMESTIC_WASH_BARREL':'Wash vessel + barrel','WORK_BOUNDARY':'Route-cut enclosure','SHARED_WORKBENCH':'Shared workbench','TIMBER_RACK_AND_STORE':'Timber rack + tool store'}
COLORS={'DOMESTIC_BOUNDARY':'#725440','DOMESTIC_DRYING_FRAME':'#aaa58f','DOMESTIC_WASH_BARREL':'#8b938a','WORK_BOUNDARY':'#725440','SHARED_WORKBENCH':'#ad8551','TIMBER_RACK_AND_STORE':'#65472e'}
def run():
 p=load(HERE/'resolved_placements.json');s=load(HERE/'source_plan.json');fig=plt.figure(figsize=(15,12),facecolor='#f4f0e6')
 for ci,c in enumerate(s['courts']):
  w,d=c['dimensions'];ax=fig.add_subplot(2,2,ci+1);ax.set_facecolor('#f4f0e6');ax.add_patch(Polygon(rect(-w/2,-d/2,w/2,d/2),fc='#d8d1bd',ec='#716c60',lw=1.2))
  for r in p['protected_routes']:
   for q in r['polygons']:ax.add_patch(Polygon(inv(q,c),fc='#88bac2',ec='none',alpha=.28))
  for pl in p['placements']:
   if pl['court_id']!=c['id']:continue
   qs=transformed(pl['native_collision_local_polygons_xz_m'],pl['local_center_xz_m'],pl['local_yaw_rad'])
   for q in qs:ax.add_patch(Polygon(q,fc=COLORS[pl['local_component_id']],ec='#493c2d',lw=.35))
   if 'BOUNDARY'not in pl['id']:
    x,z=pl['local_center_xz_m'];dy=.55 if 'RACK' in pl['id']else -.8
    if ci==0:dy=-.8 if 'DRYING'in pl['id']else-.85
    ax.annotate(LABELS[pl['local_component_id']],(x,z),xytext=(x,z+dy),ha='center',fontsize=9,bbox=dict(fc='#f4f0e6',ec='none',alpha=.95,pad=2),arrowprops=dict(arrowstyle='-',color='#4b5149'))
  ax.set_xlim(-w/2-.6,w/2+.6);ax.set_ylim(-d/2-.8,d/2+.9);ax.set_aspect('equal');ax.grid(alpha=.16);ax.set_xlabel('Court-local X (m)');ax.set_ylabel('Court-local Z (m)');ax.set_title(('Market domestic court | 40 m²'if ci==0 else'Bank shared dry-work court | 70 m²'),fontsize=14,pad=12)
  ax=fig.add_subplot(2,2,ci+3,projection='3d');ax.set_facecolor('#f4f0e6');polys=[];colors=[]
  for xx in np.arange(-w/2,w/2,.5):
   for zz in np.arange(-d/2,d/2,.5):
    polys.append([[xx,zz,-.001],[xx+.5,zz,-.001],[xx+.5,zz+.5,-.001],[xx,zz+.5,-.001]]);colors.append('#d8d1bd')
  light=np.array([-.6,1,.6]);light/=np.linalg.norm(light)
  for pl in p['placements']:
   if pl['court_id']!=c['id']:continue
   r=load(ROOT/p['assets'][pl['asset_key']]['render_path']);cx,cz=pl['local_center_xz_m']
   for g in r['groups']:
    raw=r['materials'][g['material']];col=raw.get('color',raw.get('albedo','#888888'))if isinstance(raw,dict)else raw;col=col.lstrip('#');rgb=np.array([int(col[k:k+2],16)/255 for k in(0,2,4)])
    for q in g['quads']:
     v=np.array(q);normal=np.cross(v[1]-v[0],v[2]-v[1]);normal/=np.linalg.norm(normal);shade=.7+.3*max(0,np.dot(normal,light));polys.append([[v[0]+cx,v[2]+cz,v[1]]for v in q]);colors.append(tuple(rgb*shade))
  ax.add_collection3d(Poly3DCollection(polys,facecolors=colors,edgecolors='none',zsort='average'));ax.set_xlim(-w/2-.3,w/2+.3);ax.set_ylim(-d/2-.3,d/2+.3);ax.set_zlim(-.25,3);ax.set_box_aspect((w,d,3));ax.view_init(elev=32,azim=-63);ax.set_axis_off();ax.set_title('Exact common-native quads at unit scale',fontsize=11,pad=0)
 fig.suptitle('Two useful lower-city yards | court phase 01',fontsize=21,y=.97);fig.text(.08,.045,'Blue: protected entrance lanes and court links. All equipment and enclosure solids remain outside them.\nGround shown for orientation only: R16 owns the original +2.5 m triangles; this pack adds no paving mesh.',fontsize=11,color='#434941');fig.text(.08,.012,'Software inspection sheet, not a runtime screenshot. 6 placements · 795 quads · finite native bearing cuts: 7.25 m² · no animated props or character claim',fontsize=10,color='#66685f');fig.savefig(HERE/'court_plan.png',dpi=160,bbox_inches='tight');plt.close(fig)
if __name__=='__main__':run()
