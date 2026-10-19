"""Read-only exact source/plane, native-interface and runtime-number checks."""
import json,math,collections,numpy as np
from .finalize import *

def main():
 checks=[]
 def check(name,test,details=None):
  assert test,(name,details);checks.append(dict(name=name,passed=True,details=details))
 p=json.loads((D/'profile_candidate.json').read_bytes());n=json.loads((D/'free_collinear_normalization.json').read_bytes());b=json.loads((D/'activation_binding.json').read_bytes());ledger=json.loads((D/'producer_row_retirement_ledger.json').read_bytes());side=json.loads((D/'native_apron_side_closure.json').read_bytes());rows=p['records'];ri=a.geo._SpatialIndex(4)
 for i,r in enumerate(rows):ri.add(i,r['polygon_xz_m'])
 overlap=[]
 for i,r in enumerate(rows):
  for j in ri.candidates(r['polygon_xz_m']):
   if j<=i:continue
   q=g.clip(r['polygon_xz_m'],rows[j]['polygon_xz_m'])
   if q and g.area(q)>1e-9:overlap.append(dict(ids=[r['id'],rows[j]['id']],area_m2=g.area(q)))
 check('finite_new_owner_partition',not overlap,overlap)
 grades=[];grades32=[];wrong=[];zeros32=0;planeerr=0;areaerr=0
 for r in rows:
  aa=0
  for t in r['triangles_xyz_m']:
   pts=[[v[0],v[2]]for v in t];aa+=g.area(pts);q=np.array(t,dtype=float);nn=np.cross(q[1]-q[0],q[2]-q[0]);check('upward_source_'+r['id']+'_'+str(len(grades)),nn[1]>0);gr=math.hypot(nn[0],nn[2])/nn[1];grades.append(gr);planeerr=max(planeerr,max(abs(v[1]-s.val(r['plane_y_xz_m'],[v[0],v[2]]))for v in t));qq=np.array(t,dtype=np.float32);nf=np.cross(qq[1]-qq[0],qq[2]-qq[0])
   if np.all(nf==0):zeros32+=1
   elif nf[1]<=0:wrong.append(dict(owner=r['id'],triangle_xyz_m=t,normal32=nf.tolist()))
   else:grades32.append(math.hypot(float(nf[0]),float(nf[2]))/float(nf[1]))
  areaerr=max(areaerr,abs(aa-g.area(r['polygon_xz_m'])))
 check('all_exact_source_planes_at_or_below_12_percent',max(math.hypot(*r['plane_y_xz_m'][:2])for r in rows)<=.120000000001)
 check('serialized_source_fan_gradient',max(grades)<=.12000001,dict(maximum=max(grades)))
 check('every_new_float32_top_remains_upward_and_nonzero',not wrong and zeros32==0,dict(wrong=wrong,zeros=zeros32,maximum_grade=max(grades32)))
 check('plane_and_fan_area_parity',planeerr<1e-12 and areaerr<1e-9,dict(plane_residual_m=planeerr,area_residual_m2=areaerr))
 check('bounded_redundant_collinear_normalization',n['maximum_distance_m']<=1e-9 and n['total_absolute_area_delta_m2']<1e-8,dict(maximum_distance_m=n['maximum_distance_m'],absolute_area_delta_m2=n['total_absolute_area_delta_m2']))
 seamresults=[];spill=0;nativeoverlap=0
 for dom,r in zip(p['domains'],s.survey['interfaces']):
  local=[o for o in rows if o['road_id']==dom['id']]
  for o in local:
   spill+=sum(g.area(q)for q in g.subtract([o['polygon_xz_m']],dom['polygons']))
   for nt in s.profile['triangles']:
    q=g.clip(o['polygon_xz_m'],[[v[0],v[2]]for v in nt['triangle_xyz_m']]);nativeoverlap+=g.area(q)if q else 0
  for edge in r['native_boundary_segments']:
   u,v=edge['vertices_xyz_m'];pts=[[u[0],u[2]],[v[0],v[2]]];knots={0.,1.}
   for aa in dom['planes']:
    for bb in dom['planes']:
     x=s.val(s.minus(aa,bb),pts[0]);y=s.val(s.minus(aa,bb),pts[1])
     if x*y<0:knots.add(x/(x-y))
   residual=0
   for t in knots:
    q=[pts[0][i]+t*(pts[1][i]-pts[0][i])for i in range(2)];height=min(s.field(dom['planes'][:3],q),s.val(dom['planes'][3],q));residual=max(residual,abs(height-(u[1]+t*(v[1]-u[1]))))
   check('native_piecewise_edge_'+dom['id']+'_'+str(edge['native_profile_section']),residual<1e-10,residual);seamresults.append(dict(road_id=dom['id'],edge=edge,maximum_residual_m=residual))
 check('no_native_floor_or_outside_ribbon_spill_beyond_recorded_roundoff',spill<1e-8 and nativeoverlap<1e-8,dict(outside_ribbon_area_m2=spill,native_floor_intersection_m2=nativeoverlap))
 check('exact_native_apron_clearance',min(x['minimum_cover_m']for x in p['apron_support_pieces'])>.033,dict(minimum_cover_m=min(x['minimum_cover_m']for x in p['apron_support_pieces']),uncovered_numerical_residuals=[dict(road_id=r['road_id'],area_m2=r['unsupported_area_m2'])for r in p['statistics']]))
 check('all_structural_edge_unknowns_closed',not side['unresolved_intervals'],dict(original=side['original_unknown_count'],closed=len(side['closed_intervals'])))
 patches=[]
 for rr in b['patches']:
  path=ROOT/rr['path'];check('bound_patch_'+rr['path'],sha(path)==rr['sha256']);patches.append(json.loads(path.read_bytes()))
 ids={x['id']:merger.canonical_sha(x)for x in patches}
 for x in patches:
  for pid,h in x.get('requires_patch_canonical_sha256',{}).items():check('dependency_'+x['id']+'_'+pid,ids[pid]==h)
 # Actual exact source targets and only these rows are replaced.
 source=json.loads((ROOT/ledger['source_binding']['path']).read_bytes());srcpatches={}
 for r in ledger['rows']:
  if r['location']=='original_untouched_base':continue
  i=r['patch_index']
  if i not in srcpatches:srcpatches[i]=json.loads((ROOT/source['patches'][i]['path']).read_bytes())
  pp=srcpatches[i]
  if r['location']=='appended_surfaces':t=pp['appended_surfaces'][r['material']][r['source_triangle_index']*3:r['source_triangle_index']*3+3]
  else:t=pp['surface_edits'][r['source_edit_array_index']]['replacement_triangles_xyz_m'][r['replacement_triangle_index']]
  check('source_row_'+str(len(checks)),t==r['source_triangle_xyz_m']and a.canonical_sha(t)==r['source_triangle_sha256'])
 final23=C/'registered_topography/revisions/r17_district_batches/coherent_final24_r02/generated_bank_source_ledger_r01.json';f=json.loads(final23.read_bytes());fk={(r['producer_index'],r['source_triangle_sha256'])for r in f['rows']};collision=[r for r in ledger['rows']if(r.get('patch_index'),r['source_triangle_sha256'])in fk];check('final23_row_disjointness',not collision,dict(other_ledger=ref(final23),other_rows=len(f['rows']),local_rows=len(ledger['rows'])))
 summary=dict(check_count=len(checks),new_owners=len(rows),new_top_triangles=len(grades),maximum_source_triangle_grade=max(grades),maximum_float32_triangle_grade=max(grades32),normalization_area_accounting_m2=n['total_absolute_area_delta_m2'],new_road_area_m2=sum(g.area(r['polygon_xz_m'])for r in rows),native_edge_maximum_residual_m=max(r['maximum_residual_m']for r in seamresults),native_apron_minimum_cover_m=min(x['minimum_cover_m']for x in p['apron_support_pieces']),exact_source_rows=len(ledger['rows']))
 dump(D/'source_tests.json',dict(status='PASS_BOUNDED_SOURCE_GEOMETRY_RUNTIME_PENDING',checks=checks,summary=summary,native_edge_results=seamresults,sources=[ref(D/'activation_binding.json'),ref(D/'profile_candidate.json'),ref(D/'producer_row_retirement_ledger.json'),ref(D/'free_collinear_normalization.json')],limits=['Float32 gradients differ from source design planes by local quantization; measured maximum is disclosed, not a 12% runtime claim.','The eight original road-remnant directions passed separately. These two new side grades require actual composed-scene unchanged-controller replay.','No cart, NPC or central moving drawbridge claim.']))
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
