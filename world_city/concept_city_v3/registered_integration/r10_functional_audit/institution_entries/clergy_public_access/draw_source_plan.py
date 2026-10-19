"""Source-coordinate diagram, never a replacement for a rendered scene review."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
H=Path(__file__).resolve().parent
ctx=json.loads((H/'candidate_r01/source_snapshot/context_frozen.json').read_bytes())['sites']['clergy'];f=H/'candidate_r01';p=json.loads((f/'surface_patch.json').read_bytes());r=json.loads((f/'routes.json').read_bytes());pk=json.loads((f/'pack.json').read_bytes());fig,ax=plt.subplots(figsize=(9,12))
for b in ctx['bodies']:
 if b['id']=='FIELD_SITE_CLERGY_035:12:bed:1':continue
 ax.add_patch(Polygon(b['polygon_xz_m'],facecolor='#555555',edgecolor='black',linewidth=.4))
for o in p['ownership']:
 for q in o['ownership_polygons_xz_m']:ax.add_patch(Polygon(q,facecolor='#e4b863'if o['access']=='unrestricted_public'else'#adcf9b',edgecolor='none',alpha=.8))
i=pk['instance_relocations'][0];ax.add_patch(Polygon(i['source_footprint_xz_m'],fill=False,edgecolor='#c33',linestyle='--'));ax.add_patch(Polygon(i['replacement_footprint_xz_m'],facecolor='#4c8a3b',edgecolor='black'));old=i['source_instance']['position_m'];new=i['replacement_instance']['position_m'];ax.annotate('',xy=(new[0],new[2]),xytext=(old[0],old[2]),arrowprops={'arrowstyle':'->','color':'#b32c27','linewidth':2})
for rr in r['routes']:
 if rr['id']not in ['R10_CLERGY_PUBLIC_APPROACH','R10_CLERGY_GATE_ADMISSION']:continue
 pts=rr['points'];ax.plot([q[0]for q in pts],[q[2]for q in pts],color='#0869ad'if rr['public_access']=='unrestricted_public'else'#8b36a7',linewidth=2)
a=r['routes'][1]['points'][0];b=r['gate_center_xyz_m'];ax.scatter([a[0],b[0]],[a[2],b[2]],c=['#0869ad','#8b36a7'],zorder=10);ax.annotate('Existing public forecourt\nY 14 m',xy=(a[0],a[2]),xytext=(163,-205),arrowprops={'arrowstyle':'->'});ax.annotate('Existing 4 m gate\nPublic / admitted transition',xy=(b[0],b[2]),xytext=(175,-122),arrowprops={'arrowstyle':'->'});ax.annotate('One 6 x 3 m bed\nshifted 2 m west',xy=(184.5,-149.5),xytext=(162,-141),arrowprops={'arrowstyle':'->'})
ax.set_title('Clergy high-level access: source geometry only\n2 m clear route, 79.672 m public + 3 m admitted');ax.set_xlim(159,215);ax.set_ylim(-116,-208);ax.set_aspect('equal');ax.grid(alpha=.25);ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');fig.tight_layout();fig.savefig(H/'source_plan.png',dpi=160)
