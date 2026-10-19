import json,os
from pathlib import Path
os.environ['MPLCONFIGDIR']='/tmp/matplotlib-city-v3'
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).parent;p=json.loads((P/'plan.json').read_text());fig,ax=plt.subplots(figsize=(13,12))
for d in p['districts']:ax.fill(*zip(*d['polygon_xz_m']),color=d['color'],alpha=.28)
for s in p['spaces']:ax.fill(*zip(*s['polygon_xz_m']),color='#c7c8a2',ec='#78785b',lw=.5)
for b in p.get('blocks',[]):ax.plot(*zip(*(b['polygon_xz_m']+[b['polygon_xz_m'][0]])),color='#d2b589',lw=.4)
for r in p['roads']:ax.plot(*zip(*r['polyline_xz_m']),color='#fdf3d7',lw=max(.5,r['width_m']*.45),solid_capstyle='round')
for poly in [p['water_reservations']['reservoir_outer_polygon_xz_m']]:ax.fill(*zip(*poly),color='#4b96aa')
ax.plot(*zip(*p['water_reservations']['service_canal_polyline_xz_m']),color='#4b96aa',lw=6)
for plot in p['plots']:
 if plot['property_type']=='noble_estate':ax.fill(*zip(*plot['polygon_xz_m']),color='#96aa6e',ec='#555',lw=1)
for b in p['buildings']:
 c='#746052' if 'poor' in b['function'] else '#77706d' if 'noble' in b['function'] or b.get('replace_by_assembly_key') else '#a76343'
 ax.fill(*zip(*b['footprint_xz_m']),color=c,ec='#3a3027',lw=.15)
for s in p['spaces']:
 bb=s['polygon_xz_m'];ax.text(sum(v[0] for v in bb)/len(bb),sum(v[1] for v in bb)/len(bb),s['id'].replace('S_',''),fontsize=6,ha='center',color='#222')
bb=p['boundary_xz_m'];ax.plot(*zip(*(bb+[bb[0]])),color='#444',lw=3)
ax.set(xlim=(-500,500),ylim=(400,-410),aspect='equal',title=f"Contour-block source review | {len(p['buildings'])} masses, {len(p['blocks'])} irregular blocks")
fig.tight_layout();fig.savefig(P/'plan_overview.png',dpi=180)
