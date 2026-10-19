"""Whole-block area from exact immutable native roof faces, with a finite plan view."""
import json,math
from collections import defaultdict
from pathlib import Path
from .grammar import HERE,ROOT,PLAN,ORDINARY,ref,write,g,estate,rect,xform
from world_city.concept_city_v3.assemblies.property.registered.poor_block015_east.author_density import disjoint

def roof_rects(render):
 pitch=render['pitch'];cells=set()
 for group in render['groups']:
  if not group['material'].startswith('slate'):continue
  for q in group['quads']:
   if max(v[1] for v in q)-min(v[1] for v in q)>1e-8:continue
   x0,x1=[round(f(v[0] for v in q)/pitch) for f in(min,max)];z0,z1=[round(f(v[2] for v in q)/pitch) for f in(min,max)]
   cells.update((x,z) for x in range(x0,x1) for z in range(z0,z1))
 rows=defaultdict(list)
 for x,z in cells:rows[z].append(x)
 active={};out=[]
 for z in range(min(rows),max(rows)+2):
  xs=sorted(rows[z]);runs=[]
  for x in xs:
   if runs and runs[-1][1]==x:runs[-1]=(runs[-1][0],x+1)
   else:runs.append((x,x+1))
  for run,start in list(active.items()):
   if run not in runs:out.append(rect(run[0]*pitch,start*pitch,run[1]*pitch,z*pitch));del active[run]
  for run in runs:active.setdefault(run,z)
 assert abs(sum(g.polygon_area(q) for q in out)-len(cells)*pitch*pitch)<1e-8
 return out

def run():
 p=json.loads((HERE/'resolved_placements.json').read_text());s=json.loads((HERE/'proposal.json').read_text());old=json.loads(ORDINARY.read_text());plan=json.loads(PLAN.read_text());plots={q['id']:q for q in plan['plots']};blocks={q['id']:q for q in plan['blocks']};retired=set(p['replaced_placement_ids']);assets={**old['assets'],**p['assets']};cache={};proofs={};reports=[];drawdata=[]
 def polygons(inst):
  key=inst['asset_key'];a=assets[key]
  if key not in cache:
   assert ref(ROOT/a['render_path'])['sha256']==a['render_sha256'];render=json.loads((ROOT/a['render_path']).read_text());cache[key]=roof_rects(render);proofs[key]=dict(render=ref(ROOT/a['render_path']),roof_projection_area_m2=sum(g.polygon_area(q) for q in cache[key]),rectangles=len(cache[key]))
  return [[xform(q,[inst['position_m'][0],inst['position_m'][2]],inst['yaw_rad']) for q in poly] for poly in cache[key]]
 for bid in sorted({q['block_id'] for q in s['properties']}):
  block=blocks[bid];triangles=estate.triangulate(block['polygon_xz_m']);before=[q for q in old['placements'] if plots[q['source_plot_id']].get('block_id')==bid];after=[q for q in before if q['id'] not in retired]+[q for q in p['placements'] if q['source_block_id']==bid];report=dict(block_id=bid,block_area_m2=block['area_m2'],courts=[q['court'] for q in s['properties'] if q['block_id']==bid]);shapes={}
  for label,instances in [('before',before),('after',after)]:
   polys=disjoint([q for inst in instances for q in polygons(inst)]);clipped=[q for poly in polys for tri in triangles if g.polygon_area(q:=g.convex_intersection(poly,tri))>1e-7];area=sum(g.polygon_area(q) for q in clipped);report[label+'_roof_area_m2']=area;report[label+'_roof_coverage']=area/block['area_m2'];shapes[label]=clipped
  m=next(q for q in s['whole_block_metrics'] if q['block_id']==bid);report.update(before_body_area_m2=m['before_body_area_m2'],after_body_area_m2=m['after_body_area_m2'],before_body_coverage=m['before_body_area_m2']/block['area_m2'],after_body_coverage=m['after_body_area_m2']/block['area_m2'],new_service_court_area_m2=m['new_explicit_service_court_area_m2'],new_platform_area_m2=m['new_platform_area_m2']);reports.append(report);drawdata.append((bid,block,shapes))
 result=dict(schema='riverstone.merchant_actual_roof_coverage.v1',pack=ref(HERE/'resolved_placements.json'),proposal=ref(HERE/'proposal.json'),source_plan=ref(PLAN),baseline_native_pack=ref(ORDINARY),analyzer=ref(Path(__file__)),method='Exact XZ union of horizontal slate-material cached native quad projections, reconstructed on each immutable mesh lattice then rigidly transformed, united and clipped to traced block polygons. Vertical roof risers project to zero area. No AABB roof substitute.',blocks=reports,asset_proofs=proofs,limits=['This is plan-projected roof coverage, not concept-image roof segmentation or isometric occlusion.','The seven native compounds do not resolve every remaining backland or lower residual yard.']);write(HERE/'coverage_report.json',result)
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Polygon
 fig,axes=plt.subplots(len(drawdata),2,figsize=(14,16),constrained_layout=True)
 for ri,(bid,block,shapes) in enumerate(drawdata):
  report=reports[ri]
  for ci,label in enumerate(('before','after')):
   ax=axes[ri][ci];ax.add_patch(Polygon(block['polygon_xz_m'],facecolor='#d7ccb0',edgecolor='#474a3c'))
   for road in plan['roads']:
    for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):ax.add_patch(Polygon(g.road_ribbon(a,b,road['width_m']),facecolor='#f4edda',edgecolor='none'))
   for poly in shapes[label]:ax.add_patch(Polygon(poly,facecolor='#985b43',edgecolor='#683f30',linewidth=.25))
   if label=='after':
    for prop in s['properties']:
     if prop['block_id']!=bid:continue
     ax.add_patch(Polygon(prop['polygon_xz_m'],facecolor='none',edgecolor='#41766a',linewidth=.8));ax.add_patch(Polygon(prop['court']['polygon_xz_m'],facecolor='#b6bc91',edgecolor='#68805a',linewidth=.5))
     for r in prop['internal_routes']:
      for poly in r['ribbon_polygons_xz_m']:ax.add_patch(Polygon(poly,facecolor='#e6c971',edgecolor='none',alpha=.45))
     line=prop['external_gate_link']['polyline_xz_m'];ax.plot(*zip(*line),color='#1d5f86',linewidth=2)
   q=block['polygon_xz_m'];ax.set_xlim(min(v[0] for v in q)-8,max(v[0] for v in q)+8);ax.set_ylim(max(v[1] for v in q)+8,min(v[1] for v in q)-8);ax.set_aspect('equal');ax.set_title(f"{bid} {label} | native roof {report[label+'_roof_coverage']:.1%}, body {report[label+'_body_coverage']:.1%}");ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)')
 fig.suptitle('Seven reusable merchant courts | Exact native roofs and reserved access\nBrown: roof projection; green: goods court; gold: full-width routes; blue: public handoff. Floor/retaining review pending.',fontsize=13);fig.savefig(HERE/'coverage_plan.png',dpi=130);plt.close(fig)
 print(json.dumps([dict(block_id=q['block_id'],before_roof=q['before_roof_coverage'],after_roof=q['after_roof_coverage'],before_body=q['before_body_coverage'],after_body=q['after_body_coverage'],courts_m2=q['new_service_court_area_m2']) for q in reports],indent=2));return result
if __name__=='__main__':run()
