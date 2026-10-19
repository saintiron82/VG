"""New labelled vector source diagrams, never a substituted 3D visual review."""
import json,math
from . import context as c
from world_city.concept_city_v3.assemblies.property.registered import author as a
HERE=c.HERE

def poly(p,fill,stroke='none',width=.35):return '<polygon points="'+' '.join(f'{x:.5f},{z:.5f}' for x,z in p)+f'" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'
def label(x,z,text,size=4):return f'<text x="{x}" y="{z}" font-family="sans-serif" font-size="{size}" fill="#172020">{text}</text>'
def run():
 d=c.load();pack=json.loads((HERE/'generated/source_pack.json').read_text());svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1660" height="1420" viewBox="-430 -390 830 710">','<rect x="-430" y="-390" width="830" height="710" fill="#f2eee3"/>']
 for s in d['plan']['spaces']:
  if s['id'] in ('SITE_CLERGY','SITE_CEMETERY','SITE_MONASTERY','SITE_COMMON'):svg.append(poly(s['polygon_xz_m'],'#dce3c9','#879075'))
 colors={'public_road_and_half_metre_shoulder':'#b7ad98','native_landmark_outer_envelope':'#a89483','native_landmark_floor_owner':'#c4b6a0','native_ordinary_outer_envelope':'#b5ada5','finite_water':'#86adbc','native_door_approach_pending_vertical_repair':'#c46a58'}
 for e in d['exclusions']:
  if e['kind'] in colors:svg.append(poly(e['polygon_xz_m'],colors[e['kind']]))
 for s in pack['sites']:
  svg.append(poly(s['polygon_xz_m'],'#cbdcb0','#566d3d',.65))
  for r in s['internal_paths']:
   for p in r['ribbon_polygons_xz_m']:svg.append(poly(p,'#ece2c1'))
  con=s['external_connection']
  for p in con.get('ribbon_polygons_xz_m',[]):svg.append(poly(p,'#e1c985','#8f762e',.2))
  for p in con.get('external_surface',{}).get('polygon_regions_xz_m',[]):svg.append(poly(p,'#e1c985','#8f762e',.3))
  for p in s['placements']:svg.append(poly(p['footprint_xz_m'],'#728649' if p['role']=='bed' else '#4d6c44' if p['ground_anchor']['support_kind']=='trunk_root' else '#d5cdb8','#47503c',.15))
  g=s['gates'][0];svg.append(poly(a.geom.road_ribbon(g['inside_point_xz_m'],g['outside_point_xz_m'],g['width_m']),'#ece2c1'))
  x,z=s['position'];svg.append(label(x-s['width']/3,z-4,s['id'],3))
 svg.append(label(-420,-375,'REGISTERED SOURCE PLAN | 7 finite blocks | 301 native instances | 36 burials',7));svg.append(label(-420,303,'Source geometry only. Native approach grades, sampled traversal and actual 3D view remain pending.',5));svg.append('</svg>');(HERE/'generated/landscape_source_plan.svg').write_text('\n'.join(svg))
 s=next(s for s in pack['sites'] if s['kind']=='public_park');con=s['external_connection'];rec=con['external_surface'];candidate=con['candidate'];svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1160" viewBox="0 0 800 580">','<rect width="800" height="580" fill="#f2eee3"/>',label(22,28,'PUBLIC TERRACE PARK: complete finite access reservation',17),label(22,50,'51.76 m run | 3 m clear width | 5 m gate pocket | 0.5 m public landing',11),'<defs><clipPath id="parkViewport"><rect x="20" y="72" width="765" height="315"/></clipPath></defs><g clip-path="url(#parkViewport)"><g transform="translate(24 78) scale(4.2) translate(402 102)">']
 for e in d['exclusions']:
  if e['kind'] in colors:svg.append(poly(e['polygon_xz_m'],colors[e['kind']],width=.1))
 svg.append(poly(s['polygon_xz_m'],'#cbdcb0','#566d3d',.5))
 for p in s['placements']:svg.append(poly(p['footprint_xz_m'],'#4d6c44' if p['ground_anchor']['support_kind']=='trunk_root' else '#bfb598'))
 for r in s['internal_paths']:
  for p in r['ribbon_polygons_xz_m']:svg.append(poly(p,'#ece2c1'))
 for p in rec['polygon_regions_xz_m']:svg.append(poly(p,'#e4c977','#816e32',.2))
 for o in rec['public_surface_override_regions']:
  for p in o['polygons_xz_m']:svg.append(poly(p,'#cf785c','#863e30',.15))
 svg.append(label(-394,-96,'Park floor Y=9 m',2.8));svg.append(label(-292,-59,'3 m full-width ramp',2.5));svg.append(label(-284,-39,'WEST_MONASTERY_EDGE:5',2.5));svg.append('</g></g>')
 # Full-width cut/fill section samples. All three rails are shown, rather than a centerline-only pass.
 x0,x1,ybase=55,750,505;svg.append(label(24,410,'Source cut/fill along the full ramp (three rails; negative = cut)',12));start,end=candidate['external_centerline_xz_m'][1:];u=a.unit(start,end);run=math.dist(start,end);samples=candidate['support_samples_xyz_existing_delta'][:3*(math.ceil(run/2)+1)]
 for value in (0,-.25,-.5,-.75):
  y=ybase-value*85;svg.append(f'<path d="M{x0},{y}H{x1}" stroke="#b9b5a8" stroke-width=".6"/>');svg.append(label(20,y+3,f'{value:.2f} m',9))
 for rail,color in enumerate(('#a35437','#405e8e','#3f783d')):
  coords=[]
  for x,y,z,existing,delta in samples[rail::3]:
   t=max(0,min(1,sum((p-q)*v for p,q,v in zip((x,z),start,u))/run));coords.append((x0+t*(x1-x0),ybase-delta*85))
  svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in coords)+f'" fill="none" stroke="{color}" stroke-width="1.5"/>')
 svg.append(label(24,447,f'Maximum sampled absolute cut/fill {rec["maximum_cut_fill_m"]:.3f} m; source ramp grade {rec["maximum_service_ramp_grade"]*100:.3f}%; landing {rec["maximum_inherited_public_landing_grade"]*100:.3f}%.',10));svg.append(label(24,470,'Red plan area is the exact 6.061 m² public-road override. Shared road boundary review remains pending.',10));svg.append('</svg>');(HERE/'generated/park_access_plan.svg').write_text('\n'.join(svg))
if __name__=='__main__':run()
