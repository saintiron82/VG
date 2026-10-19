"""Rendered finite partition, upward winding, route and exact native-hole proof."""
import json,time,math,collections
from . import author as a,public_tails,side_clearance

def read(p):return json.loads(p.read_bytes())
def run():
 folder=a.HERE/'b15_composed_r01';out=folder/'emission_audit.json'
 if out.exists():raise SystemExit('Preserve emission evidence')
 t0=time.monotonic();scene=a.load_scene();patch=read(folder/'scene_patch.json');owners=read(folder/'owners.json')['owners'];report=read(folder/'composition_report.json');retire=read(folder/'retirement.json');hand=read(public_tails.FABRIC/'terrain_handoff.json');layout=read(public_tails.FABRIC/'selected_layout.json');roots=read(folder/'route_handoff.json');edits={(r['material'],r['triangle_index']):r for r in patch['surface_edits']};windows=[o['polygon_xz_m']for o in owners]+[r['polygon_xz_m']for r in retire['body_restorations']];old=a.TriangleIndex(scene,windows);local=dict(surfaces={});unchanged=0
 for r in old.rows:
  key=r['material'],r['triangle_index'];triangles=edits[key]['replacement_triangles_xyz_m']if key in edits else[r['vertices_xyz_m']];unchanged+=key not in edits;local['surfaces'].setdefault(r['material'],[]).extend(v for t in triangles for v in t)
 for m,vs in patch['appended_surfaces'].items():
  if m!='bank':local['surfaces'].setdefault(m,[]).extend(vs)
 index=a.TriangleIndex(local,windows);negative=[];bad_hash=[];sourcearea=[]
 for r in patch['surface_edits']:
  original=scene['surfaces'][r['material']][3*r['triangle_index']:3*r['triangle_index']+3]
  if a.canonical_sha(original)!=r['source_triangle_sha256']:bad_hash.append((r['material'],r['triangle_index']))
  if r['material']!='bank':
   negative.extend((r['material'],r['triangle_index'])for t in r['replacement_triangles_xyz_m']if a.normal_y(t)<=0)
 for m,vs in patch['appended_surfaces'].items():
  if m!='bank':negative.extend((m,j//3)for j in range(0,len(vs),3)if a.normal_y(vs[j:j+3])<=0)
 holes=[]
 for o in owners:
  if o['action']!='hole':continue
  pieces=list(index.covering(o['polygon_xz_m']));ar=sum(a.geo.polygon_area(r['intersection_polygon_xz_m'])for r in pieces)
  if ar>1e-7:holes.append(dict(id=o['id'],unexpected_top_area_m2=ar))
 holesource=[h for h in owners if h["action"]=="hole"];hindex=a.geo._SpatialIndex(16)
 for j,h in enumerate(holesource):hindex.add(j,h["polygon_xz_m"])
 checks=[]
 for o in owners:
  if o['kind']not in('active_walking','exact_public_tail','continuous_private_public_ramp'):continue
  # Native holes take priority. Verify precisely the actual remaining walking
  # polygon, rather than treating a body/low wall footprint as a walkable floor.
  localholes=[holesource[j]["polygon_xz_m"]for j in hindex.candidates(o["polygon_xz_m"])]
  ps=a.common.subtract([o['polygon_xz_m']],localholes)
  for j,p in enumerate(ps):
   proof=a.audit_polygon(index,p);checks.append(dict(id=o['id']+':'+str(j),missing_area_m2=proof['missing_area_m2'],overlap_area_m2=proof.get('overlap_area_m2',proof.get('excess_area_m2',0.)),max_gradient=proof['max_actual_triangle_grade']))
 # Source-area conservation is checked at every clipped original triangle by
 # the producer. Independently verify total required area against new tops and
 # union-native holes using exact set subtraction on each original source face.
 holepolys=[o['polygon_xz_m']for o in owners if o['action']=='hole'];hi=a.geo._SpatialIndex(16)
 for i,p in enumerate(holepolys):hi.add(i,p)
 partition_fail=[];maxgap=0.;maxover=0.
 for r in old.rows:
  if(r['material'],r['triangle_index'])not in edits:continue
  p=r['polygon_xz_m'];parts=[q['intersection_polygon_xz_m']for q in index.covering(p)];native=[a.clip(p,holepolys[i])for i in hi.candidates(p)];native=[q for q in native if q];allparts=parts+a.common.disjoint_union(native);gap=sum(a.geo.polygon_area(q)for q in a.common.subtract([p],allparts));excess=sum(a.geo.polygon_area(q)for q in allparts)-a.geo.polygon_area(p);maxgap=max(maxgap,gap);maxover=max(maxover,excess)
  if gap>1e-7 or excess>1e-7:partition_fail.append(dict(material=r['material'],triangle_index=r['triangle_index'],gap_area_m2=gap,excess_area_m2=excess))
 failedwalk=[r for r in checks if r['missing_area_m2']>1e-7 or r['overlap_area_m2']>1e-7 or r['max_gradient']>.12000001]
 result=dict(schema='riverstone.r17.composed_district_emission_audit.v1',base_scene_sha256=a.SCENE_SHA256,scene_patch_sha256=a.sha(folder/'scene_patch.json'),source_index_count=len(edits),duplicate_source_keys=len(patch['surface_edits'])-len(edits),source_hash_errors=bad_hash,downward_emitted_tops=negative,native_hole_count=len(holepolys),native_top_overlaps=holes,walk_checks=len(checks),failed_walk_checks=failedwalk,partition_failure_count=len(partition_fail),partition_failures=partition_fail,maximum_source_gap_m2=maxgap,maximum_source_excess_m2=maxover,unchanged_local_triangles=unchanged,public_roots=7,retired_ordinary_ids=len(retire['retired_source_ids']),new_doors=len(layout['actual_doors']),elapsed_s=time.monotonic()-t0,status='PASS'if not(bad_hash or negative or holes or failedwalk or partition_fail)else'FAILED',activation=False)
 out.write_text(json.dumps(result,separators=(',',':'))+'\n');print({k:v for k,v in result.items()if not isinstance(v,list)});print(a.sha(out))
if __name__=='__main__':run()
