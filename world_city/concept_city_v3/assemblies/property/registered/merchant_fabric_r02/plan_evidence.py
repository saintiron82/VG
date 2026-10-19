"""Whole-block before/after native roof, body and ground-ownership evidence."""
import json,math
from collections import Counter
from pathlib import Path
from .grammar import HERE,ROOT,CITY,PLAN,ORDINARY,ref,write,g,estate,roof_rects,slab_rectangles
from ..merchant_block011.prepare_handoff import union,subtract
from world_city.concept_city_v3.validation.check_landmark_access_candidate import transform
PALETTE={'clay_red':'#a16b51','wood_brown':'#74513b','slate_gray':'#68727a'}

def run():
 s=json.loads((HERE/'effective_eligibility.json').read_text());plan=json.loads(PLAN.read_text());old=json.loads(ORDINARY.read_text());plots={q['id']:q for q in plan['plots']};blocks={q['id']:q for q in plan['blocks']};cache={};proofs={}
 def geometry(p,assets):
  a=assets[p['asset_key']];key=a['render_sha256']
  if key not in cache:
   path=ROOT/a['render_path'];assert ref(path)['sha256']==key;r=json.loads(path.read_text());cache[key]=dict(roof=roof_rects(r),found=slab_rectangles(r,.49,.499));proofs[key]=ref(path)
  return dict(roof=[transform(q,p) for q in cache[key]['roof']],found=[transform(q,p) for q in cache[key]['found']])
 before=[]
 for p in old['placements']:
  bid=plots[p['source_plot_id']].get('block_id');before.append(dict(id=p['id'],block_id=bid,body=[p['actual_body_footprint_xz_m']],palette=p.get('palette_id','wood_brown'),**geometry(p,old['assets'])))
 layers=[HERE.parent/'merchant_block011/resolved_placements.json',HERE.parent/'poor_block015_east/route_repair_01/effective_placements.json',CITY/'assemblies/ordinary/registered/r1/resolved_placements.json'];baseline_refs=[]
 for path in layers:
  pack=json.loads(path.read_text());retire=set(pack['replaced_placement_ids']);before=[p for p in before if p['id'] not in retire];baseline_refs.append(ref(path))
  for p in pack['placements']:
   before.append(dict(id=p['id'],block_id=p.get('source_block_id',pack.get('source_block_id')),body=p.get('actual_body_footprint_polygons_xz_m') or [p['actual_body_footprint_xz_m']],palette=p.get('palette_id','wood_brown'),**geometry(p,pack['assets'])))
 retired=set(s['replacement_ledger']['replaced_placement_ids']);after=[p for p in before if p['id'] not in retired]
 for prop in s['properties']:
  for p in prop['placements']:after.append(dict(id=p['id'],block_id=prop['block_id'],body=p['native_body_polygons_xz_m'],found=p['native_foundation_polygons_xz_m'],roof=p['native_roof_polygons_xz_m'],palette=p['roof_palette'],property_id=prop['id']))
 reports=[]
 def clip_area(polys,boundary):
  triangles=estate.triangulate(boundary);pieces=union(polys);return sum(g.polygon_area(g.convex_intersection(q,t)) for q in pieces for t in triangles if g.positive_area_overlap(q,t,1e-9))
 for bid in sorted({p['block_id'] for p in s['properties']}):
  block=blocks[bid];row=dict(block_id=bid,block_area_m2=block['area_m2'],new_compounds=sum(p['block_id']==bid for p in s['properties']),court_area_m2=sum(p['court']['area_m2'] for p in s['properties'] if p['block_id']==bid),native_street_frontage_m=sum(p['native_street_frontage_m'] for p in s['properties'] if p['block_id']==bid))
  for label,items in [('before',before),('after',after)]:
   ps=[p for p in items if p['block_id']==bid]
   for kind in ('roof','body','found'):
    a=clip_area([q for p in ps for q in p[kind]],block['polygon_xz_m']);row[label+'_'+kind+'_area_m2']=a;row[label+'_'+kind+'_coverage']=a/block['area_m2']
  # Huge graph faces include institutions, water and open grounds. Keep their
  # whole-block figures but explicitly add a finite ordinary-owned denominator.
  ordinary=[q['polygon_xz_m'] for q in plan['plots'] if q.get('block_id')==bid and q.get('property_type')=='street_frontage_plot'];ordinary +=[p['polygon_xz_m'] for p in s['properties'] if p['block_id']==bid]
  row['ordinary_owned_domain_area_m2']=sum(g.polygon_area(q) for q in union(ordinary));row['large_precinct_face_warning']=bid in('BLOCK_003','BLOCK_005');reports.append(row)
 out=dict(schema='riverstone.merchant_fabric_r02_plan_evidence.v1',eligibility=ref(HERE/'effective_eligibility.json'),source_plan=ref(PLAN),effective_baseline_layers=baseline_refs,analyzer=ref(Path(__file__)),blocks=reports,native_render_proofs=list(proofs.values()),summary={**s['summary'],'native_roof_gain_m2':sum(q['after_roof_area_m2']-q['before_roof_area_m2'] for q in reports),'authored_body_gain_m2':sum(q['after_body_area_m2']-q['before_body_area_m2'] for q in reports),'actual_foundation_gain_m2':sum(q['after_found_area_m2']-q['before_found_area_m2'] for q in reports),'front_roof_palette_distribution':dict(Counter(next(p['roof_palette'] for p in q['placements'] if p['group']=='front') for q in s['properties']))},basis=dict(roof='Exact immutable native roof-material XZ projection union.',body='Union of each native module authored body envelope; separate from cache bounds.',found='Exact occupied native mesh footprint in open slab Y0.49…0.499 below the actual threshold.'),limits=['Plan evidence only; new common range unions and finished floor/retaining support are not compiled or promoted.','The seven earlier merchants and sealed B013/B015 rows are included in the before baseline.','Large precinct graph faces are not residential land-use denominators.']);write(HERE/'plan_evidence.json',out)
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Polygon
 def draw(ax,items,limits,detail=False):
  for b in plan['blocks']:ax.add_patch(Polygon(b['polygon_xz_m'],facecolor='#d6cbb0',edgecolor='#b7aa91',linewidth=.35))
  for q in plan['spaces']:ax.add_patch(Polygon(q['polygon_xz_m'],facecolor='#b8c1a3',edgecolor='#7d8971',linewidth=.4))
  for w in plan['water_reservations']['finite_water_polygons']:ax.add_patch(Polygon(w['polygon_xz_m'],facecolor='#76a6af',edgecolor='none'))
  for road in plan['roads']:
   for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):ax.add_patch(Polygon(g.road_ribbon(a,b,road['width_m']),facecolor='#f6eedb',edgecolor='none'))
  for p in items:
   for q in p['roof']:ax.add_patch(Polygon(q,facecolor=PALETTE.get(p['palette'],'#93735d'),edgecolor='#584b3c',linewidth=.15))
  if detail:
   for prop in s['properties']:
    ax.add_patch(Polygon(prop['polygon_xz_m'],facecolor='none',edgecolor='#176a67',linewidth=.7));ax.add_patch(Polygon(prop['court']['polygon_xz_m'],facecolor='#b8c486',edgecolor='#587e3c',linewidth=.4))
    for r in prop['internal_routes']:
     for q in r['ribbon_polygons_xz_m']:ax.add_patch(Polygon(q,facecolor='#eed18a',edgecolor='none',alpha=.5))
    ax.plot(*zip(*prop['external_gate_link']['polyline_xz_m']),color='#245a93',linewidth=1)
  ax.set_xlim(limits[0],limits[2]);ax.set_ylim(limits[3],limits[1]);ax.set_aspect('equal');ax.set_xlabel('World X (m)');ax.set_ylabel('World Z (m)')
 points=[q for p in s['properties'] for q in p['polygon_xz_m']];limits=[min(q[0] for q in points)-30,min(q[1] for q in points)-30,max(q[0] for q in points)+30,max(q[1] for q in points)+30]
 fig,axes=plt.subplots(1,2,figsize=(17,12),constrained_layout=True);draw(axes[0],before,limits);draw(axes[1],after,limits,True);axes[0].set_title('Before: sealed B013/B015 rows and seven merchants included');axes[1].set_title(f"After source proposal: {len(s['properties'])} additional native-width courts")
 fig.suptitle(f"Merchant fabric r02 | {s['summary']['continuous_native_street_front_m']:.0f} m attached street frontage | {s['summary']['service_court_area_m2']:,.0f} m² courts\nExact cached roof projection; clay / wood / slate follow recipe era. Green: goods courts. Gold: reserved passages. No new city scene placement.",fontsize=13);fig.savefig(HERE/'source_plan.png',dpi=140);plt.close(fig)
 fig,axes=plt.subplots(len(reports),2,figsize=(13,4*len(reports)),constrained_layout=True,squeeze=False)
 for i,row in enumerate(reports):
  b=blocks[row['block_id']];q=b['polygon_xz_m'];bounds=[min(v[0] for v in q)-5,min(v[1] for v in q)-5,max(v[0] for v in q)+5,max(v[1] for v in q)+5]
  if row['large_precinct_face_warning']:
   q=[v for p in s['properties'] if p['block_id']==row['block_id'] for v in p['polygon_xz_m']];bounds=[min(v[0] for v in q)-25,min(v[1] for v in q)-25,max(v[0] for v in q)+25,max(v[1] for v in q)+25]
  for j,(label,items) in enumerate([('before',before),('after',after)]):draw(axes[i][j],items,bounds,j==1);axes[i][j].set_title(f"{row['block_id']} {label}: roof {row[label+'_roof_coverage']:.1%}; body {row[label+'_body_coverage']:.1%}"+(' (large precinct face, local crop)' if row['large_precinct_face_warning'] else ''))
 fig.suptitle('Exact whole-block native roof/body areas; courts and finite frontage laid out on retained roads',fontsize=13);fig.savefig(HERE/'block_comparisons.png',dpi=115);plt.close(fig);print(json.dumps(out['summary'],indent=2));return out
if __name__=='__main__':run()
