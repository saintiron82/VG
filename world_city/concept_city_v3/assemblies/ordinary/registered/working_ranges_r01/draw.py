"""Human-readable plan and native-cache inspection sheet, no runtime GUI."""
from .design import *
from .ground import BOUNDS
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Patch
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
PALETTE={'clay_red':'#a66c51','wood_brown':'#7c6047','slate_gray':'#68737a'}

def run():
 n=load(HERE/'native_geometry.json');a=load(HERE/'access_handoff.json');s=load(HERE/'selection.json');src=load(CITY/'registered_source/plan.json');fig,ax=plt.subplots(figsize=(13,10));ax.set_facecolor('#f4f0e6')
 for p in src['plots']:
  q=p['polygon_xz_m']
  if min(v[0]for v in q)>BOUNDS[2]+15 or max(v[0]for v in q)<BOUNDS[0]-15 or min(v[1]for v in q)>BOUNDS[3]+5 or max(v[1]for v in q)<BOUNDS[1]-5:continue
  ax.add_patch(Polygon(q,facecolor='#c9c6bc',edgecolor='#a8a59d',linewidth=.5))
 for r in src['roads']:
  for u,v in zip(r['polyline_xz_m'],r['polyline_xz_m'][1:]):
   if min(u[0],v[0])>BOUNDS[2]+15 or max(u[0],v[0])<BOUNDS[0]-15 or min(u[1],v[1])>BOUNDS[3]+5 or max(u[1],v[1])<BOUNDS[1]-5:continue
   from .ground import geo
   ax.add_patch(Polygon(geo.road_ribbon(u,v,r['width_m']),facecolor='#b6b2a5',edgecolor='none'))
 for h in s['selected_holdings']:
  for p in h['polygon_parts_xz_m']:ax.add_patch(Polygon(p,facecolor='#e8d9b7',edgecolor='none'))
 for r in a['external_routes']:
  for p in r['ribbon_and_join_polygons_xz_m']:ax.add_patch(Polygon(p,facecolor='#70b4c4',edgecolor='none',alpha=.8))
 for r in a['internal_routes']:
  for p in r['ribbon_and_join_polygons_xz_m']:ax.add_patch(Polygon(p,facecolor='#91c5ca',edgecolor='none',alpha=.55))
 for i,p in enumerate(n['placements']):
  for q in p['native_foundation_polygons_xz_m']:ax.add_patch(Polygon(q,facecolor='#776c59',edgecolor='none'))
  for q in p['native_roof_polygons_xz_m']:ax.add_patch(Polygon(q,facecolor=PALETTE[p['palette_id']],edgecolor='#49483f',linewidth=.35,alpha=.94))
  x,_,z=p['position_m'];ax.text(x,z,str(i+1),ha='center',va='center',color='white',weight='bold',fontsize=14,bbox=dict(boxstyle='circle,pad=.25',fc='#2f3937',ec='none'))
 for d in n['actual_doors']:
  x,y,z=d['actual_door_xyz_m'];ax.plot(x,z,'o',color='#193b3f',markersize=3.5)
 for r in a['external_routes']:
  q=r['polyline_xz_m'][-1];ax.add_patch(plt.Circle(q,3,fill=False,color='#b54634',lw=2));ax.annotate('Terminal grade hold',q,xytext=(q[0]+8,q[1]-9),arrowprops=dict(arrowstyle='->',color='#b54634'),fontsize=9,color='#9b3928')
 if (HERE/'court_plan.json').exists():
  for c in load(HERE/'court_plan.json')['courts']:
   ax.add_patch(Polygon(c['polygon_xz_m'],facecolor='#dbbf7e',edgecolor='#94713b',linewidth=1.5,hatch='..'));cx=sum(q[0]for q in c['polygon_xz_m'])/4;cz=sum(q[1]for q in c['polygon_xz_m'])/4;ax.text(cx,cz,c['short_label'],ha='center',fontsize=8,color='#614d2d')
 ax.set_xlim(150,282);ax.set_ylim(214,125);ax.set_aspect('equal');ax.grid(alpha=.14);ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');ax.set_title('Lower-city working ranges R01 | staged native plan',loc='left',fontsize=18,pad=18)
 labels=['1  Market lodgings + low repair front','2  Older joinery + low dry store','3  Raised central loft store','4  Rebuilt craft + service lodging'];fig.text(.125,.045,'   |   '.join(labels[:2])+'\n'+'   |   '.join(labels[2:]),fontsize=10)
 ax.legend(handles=[Patch(fc='#e8d9b7',label='Holding reservation'),Patch(fc='#a66c51',label='Actual native roof'),Patch(fc='#91c5ca',label='Clear exterior door lanes'),Patch(fc='#b6b2a5',label='Preserved public road')],loc='lower right',fontsize=9);fig.text(.125,.012,'15 real closed portals · 1,063.75 m² native roof · +2.5 m verified floors · external grade and native court/gate work remain open',fontsize=10,color='#555');fig.savefig(HERE/'working_ranges_plan.png',dpi=160,bbox_inches='tight');plt.close(fig)
 roofmaps=load(ROOT/'world_city/runtime_city/revisions/r2/city_history.r2.candidate.json')['roof_material_families'];fig=plt.figure(figsize=(16,11),facecolor='#ece9df')
 for i,p in enumerate(n['placements']):
  asset=n['assets'][p['asset_key']];r=load(ROOT/asset['render_path']);ax=fig.add_subplot(2,2,i+1,projection='3d');ax.set_facecolor('#ece9df');polys=[];colors=[]
  materials=copy.deepcopy(r['materials']);materials.update(roofmaps[p['palette_id']]);light=np.array([-.6,1,.6]);light/=np.linalg.norm(light)
  for group in r['groups']:
   raw=materials[group['material']];color=raw.get('color',raw.get('albedo','#888888'))if isinstance(raw,dict)else raw;color=color.lstrip('#');rgb=np.array([int(color[k:k+2],16)/255 for k in(0,2,4)])
   for q in group['quads']:
    v=np.array(q);normal=np.cross(v[1]-v[0],v[2]-v[1]);normal/=np.linalg.norm(normal);shade=.72+.28*max(0,np.dot(normal,light));polys.append([[v[0],v[2],v[1]]for v in q]);colors.append(tuple(rgb*shade))
  collection=Poly3DCollection(polys,facecolors=colors,edgecolors='none',linewidths=0,zsort='average');ax.add_collection3d(collection);b=r['bounds'];ax.set_xlim(b['min'][0]-1,b['max'][0]+1);ax.set_ylim(b['min'][2]-1,b['max'][2]+1);ax.set_zlim(0,b['max'][1]+.5);ax.set_box_aspect((b['max'][0]-b['min'][0],b['max'][2]-b['min'][2],b['max'][1]));ax.view_init(elev=25,azim=57);ax.set_axis_off();ax.set_title(labels[i],fontsize=13,pad=-8)
 fig.suptitle('Four reusable native attached families | exact compiled common quads',fontsize=19,y=.95);fig.text(.08,.05,'Distinct frontage uses, floor counts, ridges, roof pitches and work doors. Unit-scale native modules joined as one common occupancy union.\nSoftware inspection sheet, not a city screenshot. Interiors, animated doors, court facilities and navigation remain unimplemented.',fontsize=11,color='#4a4a43');fig.savefig(HERE/'native_family_review.png',dpi=160,bbox_inches='tight');plt.close(fig)
 print('Saved working_ranges_plan.png and native_family_review.png')
if __name__=='__main__':run()
