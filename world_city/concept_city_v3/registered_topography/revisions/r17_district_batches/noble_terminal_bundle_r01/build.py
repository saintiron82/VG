import json,math
from pathlib import Path
from .coverage import audit
from .. import author as a
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
FILES={'E1':'noble_terminal_cut_r01/E1_proposal.json','E2':'noble_terminal_stairs_r01/E2_proposal.json','E4':'noble_terminal_risers_r01/E4_proposal.json','E5':'noble_terminal_exceptions_r01/E5_proposal.json','E6':'noble_terminal_risers_r03/E6_proposal.json','E7':'noble_terminal_risers_r03/E7_proposal.json'}
LIMITS={'E1':.12,'E2':.35,'E4':.12,'E5':.25,'E6':.12,'E7':.12}
CONTACT=a.HERE.parent/'public_corridors_r18/noble_public_two_sided_contacts_r01.json'
assert a.sha(CONTACT)=='04c79a0617ab04b1e0dc2c45bea0f8e1b3785289cc0ccc61ebc779c8fe7fe7d6'
rows=[];checks=[];bindings=[dict(path=str(CONTACT.relative_to(a.ROOT)),sha256=a.sha(CONTACT))]
for owner,relative in FILES.items():
 p=a.HERE/relative;d=json.loads(p.read_bytes());r=d['result'];field=r['result'];assert r['status']=='PASSED_FINITE_PROFILE_WITH_DECLARED_INCIDENT_RISERS';tris=field['triangles'];coverage=audit(d['private_domain_polygons_xz_m'],tris);gap=coverage['missing_area_m2'];outside=coverage['outside_area_m2'];overlap=coverage['positive_overlap_area_m2'];gradient=max(math.hypot(*t['plane_y_xz_m'][:2])for t in tris);negative=[t['id']for t in tris if a.normal_y(t['vertices_xyz_m'])<=0];fixed=r.get('boundary_errors',[]);finite=all(math.isfinite(v)for t in tris for q in t['vertices_xyz_m']for v in q)
 assert gap<1e-7 and outside<1e-7 and overlap<1e-7 and gradient<=LIMITS[owner]+1e-7 and not negative and not fixed and finite,(owner,gap,outside,overlap,gradient)
 for v in r['vertical_risers']:
  assert abs(v['maximum_step_m']-max(abs(v['left_heights_m'][k]-v['right_heights_m'][k])for k in [0,1]))<1e-10
  assert all(abs(a.normal_y(t))<1e-10 for t in v['triangles_xyz_m'])
 for source in [dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p)),d['source'],d['target_source']]:
  assert a.sha(a.ROOT/source['path'])==source['sha256'];bindings.append(source)
 policy='Intentional visible pedestrian steps and continuous collision envelope; no cart claim'if owner=='E2'else'Declared bounded pedestrian slope exception; no cart claim'if owner=='E5'else'Finite 12% design profile with preserved measured incident public steps'
 rows.append(dict(owner_id=owner,source_proposal=dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p)),private_domain_polygons_xz_m=d['private_domain_polygons_xz_m'],fixed_public_regions=d['fixed_public_regions'],fixed_inner_regions=d['fixed_inner_regions'],triangles=[dict(t,plane=t['plane_y_xz_m'])for t in tris],vertical_risers=r['vertical_risers'],maximum_gradient=gradient,grade_limit=LIMITS[owner],maximum_private_riser_m=r['maximum_step_m'],design_policy=policy,activation=False,runtime_approval=False))
 checks.append(dict(owner_id=owner,domain_area_m2=coverage['domain_area_m2'],triangle_count=len(tris),missing_area_m2=gap,outside_area_m2=outside,positive_overlap_area_m2=max(0.,overlap),maximum_actual_gradient=gradient,downward_top_count=len(negative),fixed_boundary_error_count=len(fixed),vertical_riser_count=len(r['vertical_risers']),maximum_private_riser_m=r['maximum_step_m'],source_bindings_pass=True))
write(HERE/'profile_bundle.json',dict(schema='finite_noble_terminal_profiles_v1',owners=rows,unchanged_owner_ids=['E3'],public_two_sided_contact_source=bindings[0],source_refs=list({r['path']:r for r in bindings}.values()),activation=False,runtime_approval=False,public_height_policy='All exact source public heights remain unchanged. Separate plane-specific private vertices and explicit risers preserve incident steps.'))
write(HERE/'geometry_review.json',dict(status='PASSED_BOUNDED_SOURCE_GEOMETRY',checks=checks,runtime_approval=False,limitations=['E2 requires intentional visible stairs with a continuous collision representation.','E5 is an explicit 25% pedestrian profile.','The existing full E1 public riser reaches 57.576 mm and requires unchanged-controller replay.','Native repainting, support/collar closure and actual controller tests are owned by downstream producers.']))
print(checks)
