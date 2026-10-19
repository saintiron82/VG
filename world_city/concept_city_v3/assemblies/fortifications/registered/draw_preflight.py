"""Projected source envelopes only, not a scene render or a cache compile."""
import json,sys,itertools,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];sys.path.insert(0,str(ROOT/'world_city/concept_city_v3/assemblies/landmarks/registered'))
from build_audit import camera_functions,pose,hull
r=json.loads((HERE/'preflight.json').read_text());plan=json.loads((ROOT/r['inputs']['source_plan']['path']).read_text());project,*_=camera_functions(json.loads((ROOT/r['inputs']['controls']['path']).read_text()))
fig,ax=plt.subplots(figsize=(15.36,10.24),dpi=100);ax.imshow(plt.imread(ROOT/'world_city/reference/revision_03/city_social_water_concept.png'));rows=[]
for s in r['observations']:
 q=s['nearest_current_wall_ground_projection'];center=q['world_xyz_m'];i=q['edge_index'];a=plan['boundary_xz_m'][i];b=plan['boundary_xz_m'][(i+1)%28];yaw=math.degrees(math.atan2(-(b[1]-a[1]),b[0]-a[0]));height=(34 if s['paired_height_center_m']<36 else 42) if s['kind']=='tower' else(22 if s['paired_height_center_m']>21 else 18);w,d=(10,10) if s['kind']=='tower' else(16,3)
 pts=[project(pose([x,y,z],center,yaw)) for x,y,z in itertools.product((-w/2,w/2),(0,height),(-d/2,d/2))];ax.add_patch(Polygon(hull(pts),closed=True,facecolor='#33ddbb',alpha=.15,edgecolor='#22ff99',linewidth=1.2))
 top,base=s['observed_top_pixel_xy'],s['observed_same_face_base_pixel_xy'];ax.plot([top[0],base[0]],[top[1],base[1]],color='yellow',linewidth=1.5);px=q['pixel_xy'];ax.plot([px[0],base[0]],[px[1],base[1]],color='magenta',linewidth=1,linestyle=':');ax.text(top[0]+4,top[1]-3,str(height)+'m',fontsize=7,color='white',bbox={'facecolor':'black','alpha':.65,'pad':1})
 rows.append({'sample_id':s['id'],'candidate_height_m':height,'projected_envelope_pixels':hull(pts),'source_ground_anchor':q,'status':'uncommitted silhouette-only comparison; residuals remain'})
ax.set_xlim(0,1536);ax.set_ylim(1024,0);ax.axis('off');fig.subplots_adjust(0,0,1,1);fig.savefig(HERE/'silhouette_comparison.png');plt.close(fig);(HERE/'silhouette_candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
