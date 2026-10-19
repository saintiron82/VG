import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from .author import HERE,BASE,PLAN,ROOT
from world_city.runtime_city.checks import placement as g

def run():
 p=json.loads(BASE.read_text());a=json.loads((HERE/'route_addendum.json').read_text());plan=json.loads(PLAN.read_text());fig,ax=plt.subplots(figsize=(8,8),constrained_layout=True);r=a['route_replacements'][0];old,new=r['original'],r['replacement']
 for road in plan['roads']:
  for u,v in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):ax.add_patch(Polygon(g.road_ribbon(u,v,road['width_m']),facecolor='#e1d4b3',edgecolor='none'))
 for w in plan['water_reservations']['finite_water_polygons']:ax.add_patch(Polygon(w['polygon_xz_m'],facecolor='#78b8ca',edgecolor='#467582',alpha=.9))
 for m in p['component_placements']:
  ax.add_patch(Polygon(m['actual_outer_footprint_xz_m'],facecolor='#b37250',edgecolor='#5e3725',alpha=.9))
 for poly in old['reserved_connection_polygons_xz_m']:ax.add_patch(Polygon(poly,facecolor='#d84e4e',edgecolor='#952727',alpha=.7))
 for poly in new['reserved_connection_polygons_xz_m']+new['reserved_round_join_polygons_xz_m']:ax.add_patch(Polygon(poly,facecolor='#f1d352',edgecolor='#9a7f13',alpha=.8))
 for label,line,color in [('Old nearest-street link',old['complete_proposed_connection_xz_m'],'#b20c22'),('New 8.01 m dry approach',new['complete_proposed_connection_xz_m'],'#384e1b')]:
  ax.plot(*zip(*line),color=color,lw=2,label=label)
 door=old['actual_door_xyz_m'];ax.scatter([door[0]],[door[2]],c='black',s=24,label='Unchanged actual native doorway');ax.set_xlim(310,332);ax.set_ylim(316,294);ax.set_aspect('equal');ax.legend(loc='upper left',fontsize=8);ax.set_title('B015 single-door correction | 1.8 m full width\nFinite canal retained; no building or road movement');ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)');fig.savefig(HERE/'dry_route_plan.png',dpi=160);plt.close(fig)
if __name__=='__main__':run()
