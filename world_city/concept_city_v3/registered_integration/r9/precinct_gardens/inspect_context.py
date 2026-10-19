"""Read-only bounded source inventory and plan drawing for private planted grounds."""
import json, math, hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];CITY=ROOT/'world_city/concept_city_v3'
def load(p):return json.loads(p.read_bytes())
def near(x,z):return (-245<x<0 and -345<z<-70) or (105<x<350 and -335<z<-90) or (-405<x<-175 and -35<z<255)
def ring(b,p):
 c,s=math.cos(p['yaw_rad']),math.sin(p['yaw_rad']);v=p['position_m'];a,h=b['min'],b['max'];return [[v[0]+c*x+s*z,v[2]-s*x+c*z] for x,z in [(a[0],a[2]),(h[0],a[2]),(h[0],h[2]),(a[0],h[2])]]
def main():
 base=CITY/'evidence/r8_final110_runtime_r01/scene.json';scene=load(base);assets=scene['common_assets'];native=[]
 for a in assets.values():
  if 'bounds'not in a:a['bounds']=load(ROOT/a['render_path'])['bounds']
 for p in scene['common_instances']:
  b=assets[p['asset_key']]['bounds'];poly=ring(b,p)
  if near(p['position_m'][0],p['position_m'][2]) or any(near(*q)for q in poly):native.append(p)
 prop=load(CITY/'assemblies/property/registered/r1/resolved_placements.json');land=load(CITY/'assemblies/landscape/registered/resolved_placements.json');plan=load(CITY/'registered_source/plan.json');routes=load(CITY/'traversal_r5/revisions/r06_r8_precinct/primary_goals_extension_r01/route_catalog_493_r02.json')['routes']
 own=[dict(id=p['property_id'],floor=p['floor_y_m'],poly=p['polygon_xz_m'])for p in prop['ownership_masks']]
 own +=[dict(id=p['id'],floor=p['floor'],poly=p['polygon_xz_m'])for p in land['sites']if p['kind']!='public_park']
 for path in ['assemblies/landmarks/registered/precinct_r05_ground/phase01/active_ground_plan.json','assemblies/landmarks/registered/precinct_r05_ground/phase02/design_plan.json']:
  for h in load(CITY/path)['holdings']:
   if h['terrain_min_m']==h['terrain_max_m']:own.append(dict(id=h['id'],floor=h['terrain_min_m'],parts=h['polygon_parts_xz_m']))
 context=dict(base_scene_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),common_assets={k:v for k,v in assets.items()if any(p['asset_key']==k for p in native)},common_instances=native,owners=own,private_routes=prop['internal_routes']+land['internal_routes'],actual_doors=prop['actual_doors'],gates=prop['gate_proposals'],public_routes=routes)
 (HERE/'source_context.json').write_text(json.dumps(context,separators=(',',':'))+'\n')
 fig,axes=plt.subplots(1,3,figsize=(21,12));windows=[(-245,0,-345,-70),(105,350,-335,-85),(-405,-175,-35,255)]
 for ax,win in zip(axes,windows):
  for o in own:
   ps=[o['poly']]if 'poly'in o else o['parts']
   for poly in ps:ax.add_patch(Polygon(poly,fc='#e1eacc',ec='#7e9871',lw=.5))
   pp=[v for poly in ps for v in poly];x=sum(q[0]for q in pp)/len(pp);z=sum(q[1]for q in pp)/len(pp)
   if win[0]<x<win[1]and win[2]<z<win[3]:ax.text(x,z,o['id'],ha='center',size=6,color='#40594a')
  for p in native:
   b=assets[p['asset_key']]['bounds'];w=b['max'][0]-b['min'][0];d=b['max'][2]-b['min'][2]
   if w*d>3000 or 'boundary'in p['asset_key']or 'infrastructure'in p['id']or p['id'].startswith('R06_'):continue
   fc='#5c8f53'if any(s in p['asset_key']for s in ['tree','05a884','cypress'])else '#7b9a64'if 'b8fc7a'in p['asset_key']else '#b7aca0'
   ax.add_patch(Polygon(ring(b,p),fc=fc,ec='#6c6660',lw=.3))
  for r in prop['internal_routes']+land['internal_routes']:
   pp=r.get('polyline_xz_m',[])
   if pp:ax.plot([q[0]for q in pp],[q[1]for q in pp],color='#ca8f56',lw=1.2)
  for r in routes:
   pp=r['points_xyz_m'];ax.plot([q[0]for q in pp],[q[2]for q in pp],color='#e0987e',lw=.4,alpha=.7)
  ax.set_xlim(win[:2]);ax.set_ylim(win[3],win[2]);ax.set_aspect('equal');ax.grid(alpha=.15)
 if (HERE/'pack.json').exists():
  pack=load(HERE/'pack.json')
  for ax in axes:
   for p in pack['add_instances']:
    poly=ring(pack['common_assets'][p['asset_key']]['bounds'],p);ax.add_patch(Polygon(poly,fc='#205d31',ec='#103e21',lw=.8));ax.scatter([p['position_m'][0]],[p['position_m'][2]],s=14,c='#205d31',marker='^')
  fig.suptitle('R9 retained ownership planting: 64 native cypresses; full canopy and all paths reserved',size=14)
 fig.tight_layout();fig.savefig(HERE/('accepted_planting_plan.png'if (HERE/'pack.json').exists()else 'owned_ground_review.png'),dpi=150);plt.close(fig)
 print('native',len(native),'owners',len(own),'assets',len(context['common_assets']))
if __name__=='__main__':main()
