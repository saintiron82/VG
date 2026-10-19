#!/usr/bin/env python3
"""Read-only source constraint drawings for editable land-use candidates."""
import json,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
os.environ['MPLCONFIGDIR']=str(ROOT/'world_city/runtime_city/landuse/.mplcache')
from world_city.runtime_city.checks import urban_void_audit as audit
from world_city.runtime_city.topography import author as grade
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
HERE=Path(__file__).parent
plan=json.loads((ROOT/'world_city/data/city_brief.v2.json').read_text())
scene=json.loads((ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json').read_text())
fabric=json.loads((ROOT/'world_city/runtime_city/revisions/r3/urban_fabric.access_repaired.json').read_text())
records,cache=audit.load_geometries(scene,fabric,plan,ROOT)
(HERE/'source_constraints.json').write_text(json.dumps([{k:v for k,v in r.items() if k!='planes'} for r in records],sort_keys=True))
voids=json.loads((ROOT/'world_city/runtime_city/evidence/urban_void_audit.json').read_text())
colors={'building_envelopes':'#70574a','original_plot_grounds':'#ddd0a8','public_road_ribbons':'#dd8844','access_reservations':'#dfb6ba','fabric_envelopes':'#5c7d42','remaining_reserved_courtyards':'#c5b995','explicit_property_grounds':'#ad9f8a','wall_envelopes':'#777777'}
for identity,bounds in [('oldtown',[-440,10,-220,240]),('wholecity',[-660,-570,660,460])]:
 fig,ax=plt.subplots(figsize=(14,14))
 for rec in sorted(records,key=lambda r:r['category'] not in ('original_plot_grounds','remaining_reserved_courtyards','explicit_property_grounds')):
  p=rec['polygon'];bb=audit.bounds(p)
  if bb[1][0]<bounds[0] or bb[0][0]>bounds[2] or bb[1][1]<bounds[1] or bb[0][1]>bounds[3]:continue
  ax.add_patch(Polygon(p,facecolor=colors.get(rec['category'],'#b7b7b7'),edgecolor='none',alpha=.65))
 if identity=='oldtown':
  for rec in plan['roads']:
   nodes={n['id']:n['position_m'] for n in plan['road_nodes']};p=nodes[rec['from_node']];q=nodes[rec['to_node']]
   if bounds[0]<p[0]<bounds[2] and bounds[1]<p[2]<bounds[3]:ax.text(p[0],p[2],rec['id'],fontsize=4)
  r=next(r for r in voids['largest_residual_regions'] if r['id']=='VOID_06')
  origin=voids['method']['grid_origin_xz_m'];res=2
  for iz,a,b in r['row_runs_iz_ix_inclusive']:
   x0,z0=origin[0]+a*res,origin[1]+iz*res
   ax.add_patch(Polygon([[x0,z0],[origin[0]+(b+1)*res,z0],[origin[0]+(b+1)*res,z0+res],[x0,z0+res]],facecolor='#80b5c4',alpha=.5,edgecolor='none'))
 ax.set_xlim(bounds[0],bounds[2]);ax.set_ylim(bounds[3],bounds[1]);ax.set_aspect('equal');ax.grid(alpha=.25);ax.set_xlabel('X metres');ax.set_ylabel('Z metres; north up');ax.set_title(identity+' source constraints; blue = strict residual mask')
 fig.savefig(HERE/(identity+'_constraints.png'),dpi=150,bbox_inches='tight');plt.close(fig)
print(len(records),'constraint records')
