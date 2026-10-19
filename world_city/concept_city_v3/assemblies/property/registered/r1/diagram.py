"""New labelled source plan, not a rendered common-scene approval."""
import json
from . import author as q
from .. import author as a

def run():
 plan=json.loads((a.CITY/'registered_source/plan.json').read_text());rs=[json.loads((q.OUT/(i+'.recipe.json')).read_text()) for i in a.IDS]
 svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="1100" viewBox="-270 -355 285 305">','<rect x="-270" y="-355" width="285" height="305" fill="#ece9df"/>']
 def poly(p,fill,stroke='none',sw=.3):return '<polygon points="'+' '.join(f'{x:.4f},{z:.4f}' for x,z in p)+f'" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
 for road in plan['roads']:
  for u,v in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):svg.append(poly(a.geom.road_ribbon(u,v,road['width_m']),'#c0b6a3'))
 for r in rs:
  svg.append(poly(r['plot']['polygon_xz_m'],'#d7dfbf','#514a3d',.6))
  for g in r['ground_regions']:svg.append(poly(g['polygon_xz_m'],'#a0b978' if 'garden' in g['land_use'] else '#c8bea9'))
  for p in r['placements']:svg.append(poly(p['footprint_xz_m'],'#426b42' if p['role'].startswith('orchard') else '#849550' if p['role'].startswith('garden') else '#9e8e79','#60584e',.15))
  for path in r['entrance_routes']:
   for ribbon in path['ribbon_polygons_xz_m']:svg.append(poly(ribbon,'#eee4c6'))
  for p in r['external_surface']['polygon_regions_xz_m']:svg.append(poly(p,'#c88b55','#9a5a31',.2))
  g=r['gates'][0];x,z=g['center_xz_m'];svg.append(f'<circle cx="{x}" cy="{z}" r="1.4" fill="#ba3b25"/>')
  x,z=r['origin_xz_m'];grade=r['external_surface']['maximum_service_ramp_grade']*100;svg.append(f'<text x="{x}" y="{z}" font-size="3.5" text-anchor="middle" font-family="sans-serif">{r["id"]}: {grade:.2f}% ramp</text>')
 svg.append('<text x="-265" y="-56" font-size="3.6" font-family="sans-serif">SOURCE ACCESS PLAN ONLY | orange: finite ramp/pocket | common view pending</text></svg>');(q.OUT/'access_source_plan.svg').write_text('\n'.join(svg))
if __name__=='__main__':run()
