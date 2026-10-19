"""Keep genuine out-of-budget margins as explicit nonwalking source-plane verges."""
from . import geometry as g
from .design import HERE as SOURCE
from world_city.concept_city_v3.registered_topography.revisions.r16_working_ranges import author as tc
reportpath=g.CITY/'registered_topography/revisions/r17_district_batches/contour_core_review_r01/report.json';report=g.load(reportpath);changed=[]
for r in report['rows']:
 if r['id'].startswith('BLOCK_006:'):continue
 out=SOURCE/'contour_revision_r01'/r['id'].split(':')[0];l=g.load(out/'selected_layout.json');h=next(h for h in l['holdings']if h['id']==r['id']);cut=[]
 for q in r['excess_regions']:
  a,b,c=q['plane_y_xz_m'];vs=[a*p[0]+b*p[1]+c-r['floor_y_m']for p in q['polygon_xz_m']];ex=max(vs)if q['kind']=='cut'else-min(vs)
  if ex<=2.5+1e-7:continue
  assert q['classification']=='holding_margin';cut.append(q)
 h['ground_owner_polygons_xz_m']=tc.subtract([h['holding_polygon_xz_m']],[q['polygon_xz_m']for q in cut]);h['nonwalking_slope_verges']=cut;h['margin_trim_proof']=g.ref(reportpath);h['ground_owner_policy']='Exclude only source-hashed nonessential margin pieces from the regrade; retain their original planes as nonwalking slope verges. Native footing, core court and necessary walking remain owned.';g.write(out/'selected_layout.json',l);a=g.load(out/'access_handoff.json');a['layout']=g.ref(out/'selected_layout.json');g.write(out/'access_handoff.json',a);p=g.load(out/'ground_proposal.json');p.update(layout=g.ref(out/'selected_layout.json'),access=g.ref(out/'access_handoff.json'))
 for cl in p['clusters']:
  cl['ground_owner_polygons_xz_m']=[q for hh in l['holdings']if hh['id']in cl['holding_ids']for q in hh.get('ground_owner_polygons_xz_m',[hh['holding_polygon_xz_m']])]
 p['retained_nonwalking_margin_verges']=[dict(holding_id=hh['id'],**q)for hh in l['holdings']for q in hh.get('nonwalking_slope_verges',[])];g.write(out/'ground_proposal.json',p);changed.append(dict(id=h['id'],trimmed_area_m2=sum(g.geo.polygon_area(q['polygon_xz_m'])for q in cut)))
g.write(SOURCE/'contour_revision_r01/margin_trim_report.json',dict(source=g.ref(reportpath),rows=changed,source_plane_preservation=True));print(changed)
