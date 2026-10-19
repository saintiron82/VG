"""Review plots derived from exact registered source, no image generation."""
import json,math,os
from pathlib import Path
os.environ['MPLCONFIGDIR']='/tmp/matplotlib-registered-city'
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .controls import MODEL
P=Path(__file__).parent;plan=json.loads((P/'plan.json').read_text())
def project(x,z,y):
 s=MODEL['scale_px_per_m'];t=math.radians(MODEL['yaw_degrees']);e=math.radians(MODEL['elevation_degrees']);cx,cy=MODEL['offset_pixel_xy']
 return [cx+s*(math.cos(t)*x-math.sin(t)*z),cy+s*(math.sin(e)*math.sin(t)*x-math.cos(e)*y+math.sin(e)*math.cos(t)*z)]
fig,ax=plt.subplots(figsize=(12,12));ax.set_facecolor('#e0d6c0')
for d in plan['districts']:
 if d['id']!='D_MIXED':ax.fill(*zip(*d['polygon_xz_m']),color=d['color'],alpha=.35)
for q in plan['water_reservations']['finite_water_polygons']:ax.fill(*zip(*q['polygon_xz_m']),color='#5593a5',alpha=.9)
for s in plan['spaces']:
 ax.fill(*zip(*s['polygon_xz_m']),color='#bdc49d' if 'MARKET' not in s['id'] else '#d5c5a0',alpha=.5,ec='#77795d',lw=.6)
for bl in plan['blocks']:ax.plot(*zip(*(bl['polygon_xz_m']+[bl['polygon_xz_m'][0]])),color='#bba47f',lw=.5)
for r in plan['roads']:ax.plot(*zip(*r['polyline_xz_m']),color='#f7efda',lw=r['width_m']*.5,solid_capstyle='round')
for p in plan['plots']:
 if p['property_type']=='noble_estate_registered':ax.fill(*zip(*p['polygon_xz_m']),color='#adba84',ec='#53594a',lw=1.2);c=p['origin_xz_m'];ax.text(*c,p['id'],ha='center',fontsize=8)
for b in plan['buildings']:ax.fill(*zip(*b['footprint_xz_m']),color='#9c674b' if b['district_id']!='D_POOR' else '#85705b',ec='#574234',lw=.2)
from .author import box
for gr in plan['landmark_components']:
 anchor=gr['world_anchor_xyz_m']
 for m in gr['masses']:
  pos=[anchor[0]+m['position_local_xyz_m'][0],anchor[2]+m['position_local_xyz_m'][2]];poly=box(pos,m['size_xyz_m'][0],m['size_xyz_m'][2],math.radians(m['yaw_degrees']));ax.fill(*zip(*poly),color='#8a8785',ec='#494949',lw=.4)
for s in plan['spaces']:
 q=s['polygon_xz_m'];c=[sum(v[i] for v in q)/len(q) for i in (0,1)];ax.text(*c,s['id'].replace('SITE_',''),fontsize=7,ha='center')
bb=plan['boundary_xz_m'];ax.plot(*zip(*(bb+[bb[0]])),color='#494940',lw=3)
ax.set(xlim=(-490,490),ylim=(560,-470),aspect='equal',title=f"Image-registered source draft | {len(plan['buildings'])} modular masses | traced precincts + inferred local links")
fig.tight_layout();fig.savefig(P/'plan_overview.png',dpi=160);plt.close(fig)
# Pixel-plane comparison uses exact camera projection of footprint ground datums.
image=plt.imread(P.parents[1]/'reference/revision_03/city_social_water_concept.png')
fig,ax=plt.subplots(figsize=(15.36,10.24));ax.imshow(image)
for r in plan['roads']:
 ys=r.get('levels_m',[4]*len(r['polyline_xz_m']));pts=[project(*q,y) for q,y in zip(r['polyline_xz_m'],ys)];ax.plot(*zip(*pts),color='#ffed88',lw=1.15,alpha=.9)
for b in plan['buildings']:
 pts=[project(*q,b['pad_floor_y_m']) for q in b['footprint_xz_m']];ax.fill(*zip(*pts),facecolor='#f5b471',edgecolor='#402c20',lw=.4,alpha=.55)
wall=plan['wall_registration'];pts=[project(*q,y) for q,y in zip(plan['boundary_xz_m'],wall['levels_m'])];ax.plot(*zip(*(pts+[pts[0]])),color='#fff8a5',lw=2)
ax.text(25,995,'REGISTERED SOURCE FOOTPRINTS | Ground-plane design hypothesis; buildings are authored modules, not recovered image geometry.',color='white',fontsize=11,bbox={'facecolor':'#111111','alpha':.8,'pad':4})
ax.set(xlim=(0,1536),ylim=(1024,0));ax.axis('off');fig.subplots_adjust(0,0,1,1);fig.savefig(P/'registered_footprint_overlay.png',dpi=100);plt.close(fig)
