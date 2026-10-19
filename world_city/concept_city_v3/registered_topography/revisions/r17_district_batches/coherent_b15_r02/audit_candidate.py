"""Exact emitted topology, upward winding, native holes and clear volumes."""
import json,time,math,collections
from .. import author as a,side_clearance
from .source_preflight import HERE,FABRIC,read,write

def run():
 t0=time.monotonic();scene=a.load_scene();patch=json.loads((HERE/'candidate_scene_patch.json').read_bytes());owners=json.loads((HERE/'owners.json').read_bytes())['owners'];report=json.loads((HERE/'composition_report.json').read_bytes());layout=read('selected_layout.json');edits={(r['material'],r['triangle_index']):r for r in patch['surface_edits']};windows=[o['polygon_xz_m']for o in owners];old=a.TriangleIndex(scene,windows);local=dict(surfaces={});unchanged=0
 for r in old.rows:
  key=r['material'],r['triangle_index'];tris=edits[key]['replacement_triangles_xyz_m']if key in edits else[r['vertices_xyz_m']];unchanged+=key not in edits;local['surfaces'].setdefault(r['material'],[]).extend(v for tr in tris for v in tr)
 original_sides=side_clearance.SideIndex(scene,windows)
 for r in original_sides.rows:
  key=r['material'],r['triangle_index'];tris=edits[key]['replacement_triangles_xyz_m']if key in edits else[r['vertices_xyz_m']];local['surfaces'].setdefault(r['material'],[]).extend(v for tr in tris for v in tr)
 for m,vs in patch['appended_surfaces'].items():local['surfaces'].setdefault(m,[]).extend(vs)
 boxes=[a.bounds(r['polygon_xz_m'])for r in old.rows];bb=[min(b[0]for b in boxes),min(b[1]for b in boxes),max(b[2]for b in boxes),max(b[3]for b in boxes)];index=a.TriangleIndex(local,[[[bb[0],bb[1]],[bb[2],bb[1]],[bb[2],bb[3]],[bb[0],bb[3]]]])
 negative=[];hashes=[]
 for r in patch['surface_edits']:
  tr=scene['surfaces'][r['material']][3*r['triangle_index']:3*r['triangle_index']+3]
  if a.canonical_sha(tr)!=r['source_triangle_sha256']:hashes.append([r['material'],r['triangle_index']])
  negative.extend([r['material'],r['triangle_index']]for tr in r['replacement_triangles_xyz_m']if a.normal_y(tr)<-1e-10)
 for m,vs in patch['appended_surfaces'].items():negative.extend([m,k//3]for k in range(0,len(vs),3)if a.normal_y(vs[k:k+3])<-1e-10)
 holes=[o for o in owners if o['action']=='hole'];hi=a.geo._SpatialIndex(16)
 for i,o in enumerate(holes):hi.add(i,o['polygon_xz_m'])
 holefails=[]
 for o in holes:
  area=sum(a.geo.polygon_area(r['intersection_polygon_xz_m'])for r in index.covering(o['polygon_xz_m']))
  if area>1e-7:holefails.append(dict(id=o['id'],unexpected_top_area_m2=area))
 print('native holes',len(holes),len(holefails),flush=True)
 checks=[];walking=[]
 for o in report['rendered_owner_parts']:
  if o['kind']not in('active_walking','functional_court','shared_public_profile','moved_level_public_entry','level_public_tail'):continue
  proof=a.audit_polygon(index,o['polygon_xz_m']);delta=0.
  for r in proof['source_pieces']:
   delta=max(delta,max(abs(a.common.height(r['plane_y_xz_m'],p)-a.common.height(o['plane_y_xz_m'],p))for p in r['polygon_xz_m']))
  checks.append(dict(id=o['id'],missing_area_m2=proof['missing_area_m2'],overlap_area_m2=proof['excess_area_m2'],max_gradient=proof['max_actual_triangle_grade'],max_expected_height_error_m=delta));walking.append(o)
 failedwalk=[r for r in checks if r['missing_area_m2']>1e-7 or r['overlap_area_m2']>1e-7 or r['max_gradient']>.12000001 or r['max_expected_height_error_m']>1e-7]
 print('walking',len(checks),len(failedwalk),flush=True)
 sideproof=side_clearance.SideIndex(local,windows).audit(walking);print('sides',len(sideproof['contacts']),flush=True)
 failures=[];maxgap=0.;maxover=0.
 for r in old.rows:
  if(r['material'],r['triangle_index'])not in edits:continue
  p=r['polygon_xz_m'];parts=[q['intersection_polygon_xz_m']for q in index.covering(p)];native=[a.clip(p,holes[i]['polygon_xz_m'])for i in hi.candidates(p)];native=[q for q in native if q];allparts=parts+a.common.disjoint_union(native);gap=sum(a.geo.polygon_area(q)for q in a.common.subtract([p],allparts));excess=sum(a.geo.polygon_area(q)for q in allparts)-a.geo.polygon_area(p);maxgap=max(maxgap,gap);maxover=max(maxover,excess)
  if gap>1e-7 or excess>1e-7:failures.append(dict(material=r['material'],triangle_index=r['triangle_index'],gap_area_m2=gap,excess_area_m2=excess))
 result=dict(base_scene_sha256=a.SCENE_SHA256,scene_patch_sha256=a.sha(HERE/'candidate_scene_patch.json'),source_index_count=len(edits),duplicate_source_keys=len(patch['surface_edits'])-len(edits),source_hash_errors=hashes,downward_emitted_tops=negative,native_hole_count=len(holes),native_top_overlaps=holefails,walk_checks=len(checks),failed_walk_checks=failedwalk,partition_failure_count=len(failures),partition_failures=failures,maximum_source_gap_m2=maxgap,maximum_source_excess_m2=maxover,unchanged_local_triangles=unchanged,public_roots=22,retired_ordinary_ids=len(layout['retired_source_ids']),new_doors=len(layout['actual_doors']),side_contact_count=len(sideproof['contacts']),elapsed_s=time.monotonic()-t0,status='PASS'if not(hashes or negative or holefails or failedwalk or failures or sideproof['contacts'])else'FAILED',activation=False)
 write('emission_audit_r01.json',result);write('side_audit_r01.json',sideproof);print({k:v for k,v in result.items()if not isinstance(v,list)},flush=True)
if __name__=='__main__':run()
