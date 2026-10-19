import json,math,collections,struct
from .author import *
from .finalize import merger,area3d
from ..final_local_sides_r03 import subtract_vertical

def main():
 failures=[];checks=[]
 def check(name,ok,**facts):checks.append(dict(name=name,pass_=bool(ok),**facts));failures.extend([]if ok else[name])
 top=json.loads((HERE/'appended_top_retirement_ledger.json').read_bytes());banks=json.loads((HERE/'bank_retirement_ledger.json').read_bytes());handoff=json.loads((HERE/'integration_handoff.json').read_bytes());binding=json.loads((HERE/'activation_binding.json').read_bytes());original=json.loads((ROOT/handoff['sources'][0]['path']).read_bytes());local=json.loads((HERE/'physical_owners.json').read_bytes());screen=json.loads((HERE/'profile_screen.json').read_bytes());bd=json.loads((HERE/'boundary_candidate.json').read_bytes());parts=[q for r in screen['rows']for q in r['changed_parts']];polys=[r['polygon_xz_m']for r in parts]
 check('exact_top_source_partition',top['maximum_area_partition_error_m2']<1e-8,maximum_error_m2=top['maximum_area_partition_error_m2']);check('original_retirements_and_nonroad_tops_unchanged',top['original_surface_edits_identical']and top['other_material_arrays_identical'])
 allpatches=[];unedited=0
 for i,(oldr,newr)in enumerate(zip(original['patches'],binding['patches'])):
  old=json.loads((ROOT/oldr['path']).read_bytes());new=json.loads((ROOT/newr['path']).read_bytes());allpatches.append(new);check('producer_'+str(i)+'_base_source_edits_unchanged',old['surface_edits']==new['surface_edits']and old['source_surface_hashes']==new['source_surface_hashes'])
  if i not in[6,15,16,20]:check('producer_'+str(i)+'_geometry_unchanged',old['appended_surfaces']==new['appended_surfaces'])
 idx={r['id']:r for r in allpatches};check('all_canonical_dependencies_bound',all(merger.canonical_sha(idx[pid])==h for r in allpatches for pid,h in r.get('requires_patch_canonical_sha256',{}).items()))
 errors=[]
 for src in banks['rows']:
  for r in src['rows']:errors.append(abs(area3d(r['source_triangle_xyz_m'])-sum(area3d(t)for t in r['replacement_triangles_xyz_m'])-next(x['removed_area_m2']for x in bd['retired_sides']if x['triangle_index']==r['source_scene_triangle_index'])))
 check('exact_bank_partition',max(errors)<1e-8,maximum_error_m2=max(errors),retired_source_triangles=sum(len(r['rows'])for r in banks['rows']))
 overlaps=[]
 for i,poly in enumerate(polys):
  for j in range(i):
   ar=g.area(g.clip(poly,polys[j]))
   if ar>1e-12:overlaps.append([i,j,ar])
 check('changed_owner_positive_area_disjoint',not overlaps,overlaps=overlaps)
 water=json.loads((CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r02/fields.json').read_bytes());wp=[t['polygon_xz_m']for f in water['profiles']for t in f['triangles']];wa=math.fsum(g.area(g.clip(q,w))for q in polys for w in wp)
 check('fixed_water_profiles_not_overlaid',wa<1e-9,intersection_area_m2=wa)
 maxgrade=max(math.hypot(*r['plane_y_xz_m'][:2])for r in parts);check('changed_planes_at_most_ten_percent',maxgrade<=.1+1e-12,maximum_gradient=maxgrade)
 contacts=[[74.24975791002086,-305.33084728894494],[75.18391583665395,-296.41949808585645],[75.30216693703365,-296.6024266228599]];ys=[max(p.val(pl,x)for pl in p.PLANES)for x in contacts];check('all_three_fixed_traffic_contacts_at_native_datum',max(abs(y-15.6)for y in ys)<1e-9,heights_m=ys)
 seams=[r for r in bd['boundary_seams']if r['kind']=='continuous'];check('public_and_water_continuous_seams',max(r['maximum_delta_m']for r in seams)<1e-7,measured_segment_count=len(seams),maximum_height_delta_m=max(r['maximum_delta_m']for r in seams));check('unknown_edge_exact_native_deck_classification',len(bd['unknown_exterior_segments'])==1 and banks['explicit_native_deck_edge']['other_owner']==['accepted_native_deck','MARKET_NORTH'])
 # New boundary faces must not add coincident positive-area sides to retained arrays.
 new=banks['new_retaining_triangles_xyz_m'];retained=[]
 for i,patch in enumerate(allpatches):
  vs=patch.get('appended_surfaces',{}).get('bank',[])
  if i==16:vs=vs[:-3*len(new)]
  for j in range(0,len(vs),3):
   t=vs[j:j+3];xs=[v[0]for v in t];zs=[v[2]for v in t]
   if max(xs)<65 or min(xs)>80 or max(zs)<-307 or min(zs)>-293:continue
   retained.append(t)
 _,ledger=subtract_vertical(new,retained);overlap=math.fsum(x['area_m2']for r in ledger for x in r['covered_by_existing']);check('new_sides_no_retained_duplicate',overlap<1e-8,coplanar_overlap_m2=overlap)
 _,selfledger=subtract_vertical(new,[]);check('new_side_positive_finite_area',all(area3d(t)>0 and all(math.isfinite(v)for p0 in t for v in p0)for t in new),count=len(new))
 # Exact retained double-coordinate rows are never rounded. Runtime sanitation is separate.
 newtops=[t for r in top['rows']for t in r['replacement_triangles_xyz_m']];check('new_top_upward',all(a.normal_y(t)>0 for t in newtops),count=len(newtops))
 report=dict(schema='riverstone.north_junction_source_tests.v1',status='PASS_SOURCE_GEOMETRY_PENDING_ACTUAL_SCENE_REPLAY'if not failures else'HELD',sources=[ref(HERE/'integration_handoff.json'),ref(Path(__file__))],checks=checks,failures=failures,changed_area_m2=screen['changed_area_m2'],changed_bounds_xz_m=screen['bounds_xz_m'],max_lowering_m=screen['max_lowering_m'],original_source_retirement_rows_changed=0,native_instances_or_assets_changed=0,controller_changed=False);dump(HERE/'source_tests.json',report);print(report['status'],len(checks),failures,'bank overlap',overlap)
 if failures:raise SystemExit(1)
 seal=dict(schema='riverstone.source_freeze.v1',status=report['status'],files=[ref(HERE/x)for x in['profile.py','author.py','entry_handoff.py','finalize.py','verify.py','profile_screen.json','physical_owners.json','appended_top_retirement_ledger.json','bank_retirement_ledger.json','boundary_candidate.json','c006_public_planes.json','activation_binding.json','integration_handoff.json','source_tests.json']]+binding['patches'],limits=['Actual composed-scene same-controller replay is required. Source geometry tests are not runtime approval.']);print(dump(HERE/'freeze_manifest.json',seal))
if __name__=='__main__':main()
