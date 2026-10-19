"""Bounded immutable appended-row correction for the fixed northern junction."""
import json,math,hashlib,copy,time
from pathlib import Path
from . import profile as p
from .. import finite_geometry_r03 as g
from ...r17_district_batches import author as a
from world_city.concept_city_v3.registered_integration.r8 import finite_boundary_index as side
HERE=p.HERE;CITY=p.CITY;ROOT=p.ROOT

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def ref(path):return dict(path=str(Path(path).relative_to(ROOT)),sha256=sha(path))
def dump(path,obj):path.write_text(json.dumps(obj,separators=(',',':'),allow_nan=False)+'\n');return ref(path)
def fan(poly,plane):
 out=[]
 for i in range(1,len(poly)-1):
  q=[poly[0],poly[i],poly[i+1]]
  if g.area(q)<=0:continue
  if g.signed_area(q)>0:q=[q[0],q[2],q[1]]
  out.append([[v[0],p.val(plane,v),v[1]]for v in q])
 return out

def main():
 start=time.monotonic();bindp=CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r02/activation_binding.json';binding=json.loads(bindp.read_bytes());srcp=ROOT/binding['patches'][15]['path'];assert sha(srcp)==binding['patches'][15]['sha256'];src=json.loads(srcp.read_bytes());screenp=HERE/'profile_screen.json';screen=json.loads(screenp.read_bytes());pubp=HERE.parent/'finite_field_candidate_r07_native_bound.json';public=json.loads(pubp.read_bytes());assert sha(pubp)==screen['source_public_sha256'];changes={r['source_owner_id']:r for r in screen['rows']};logical=[]
 for r in public['records']:
  if r['id']not in changes:continue
  row=changes[r['id']];parts=row['changed_parts'];remaining=g.subtract([r['polygon_xz_m']],[q['polygon_xz_m']for q in parts])
  for j,q in enumerate(parts):logical.append(dict(id=r['id']+':NORTH_TRANSITION:'+str(j),source_owner_id=r['id'],source_triangle_index=r['source_triangle_index'],kind='northern_junction_10pct_transition',material='road',**q))
  for j,q in enumerate(remaining):logical.append(dict(id=r['id']+':RETAINED:'+str(j),source_owner_id=r['id'],source_triangle_index=r['source_triangle_index'],kind='unchanged_public_remainder',material='road',polygon_xz_m=q,plane_y_xz_m=r['plane_y_xz_m']))
 for r in logical:r['triangles_xyz_m']=fan(r['polygon_xz_m'],r['plane_y_xz_m'])
 dump(HERE/'physical_owners.json',dict(schema='riverstone.finite_physical_owners.v1',status='UNACTIVATED_LOCAL_PROFILE',sources=[ref(pubp),ref(screenp)],replaced_source_owner_ids=sorted(changes),records=logical))
 # Actual composed producer rows, not a transient scene triangle numbering.
 out=copy.deepcopy(src);flat=src['appended_surfaces']['road'];result=[];ledger=[];source_map=[];maxerr=0.
 for ti in range(len(flat)//3):
  tri=flat[3*ti:3*ti+3];poly=[[v[0],v[2]]for v in tri]
  bb=[min(v[0]for v in poly),min(v[1]for v in poly),max(v[0]for v in poly),max(v[1]for v in poly)]
  if bb[0]>80 or bb[2]<65 or bb[1]>-293 or bb[3]<-307:result+=tri;source_map.append(dict(source_index=ti,output_start_triangle=len(result)//3-1,count=1,unchanged=True));continue
  pl=a.common.plane(tri) if g.area(poly)>g.MIN_AREA else None
  if pl is None:result+=tri;source_map.append(dict(source_index=ti,output_start_triangle=len(result)//3-1,count=1,unchanged=True));continue
  parts=p.changed_parts(poly,pl)
  if not parts:result+=tri;source_map.append(dict(source_index=ti,output_start_triangle=len(result)//3-1,count=1,unchanged=True));continue
  remaining=g.subtract([poly],[q['polygon_xz_m']for q in parts]);new=[t for q in remaining for t in fan(q,pl)]+[t for q in parts for t in fan(q['polygon_xz_m'],q['plane_y_xz_m'])];before=g.area(poly);after=sum(g.area([[v[0],v[2]]for v in t])for t in new);maxerr=max(maxerr,abs(before-after));assert abs(before-after)<1e-8,(ti,before,after)
  first=len(result)//3;result.extend(v for t in new for v in t);source_map.append(dict(source_index=ti,output_start_triangle=first,count=len(new),unchanged=False));ledger.append(dict(material='road',source_appended_triangle_index=ti,source_triangle_sha256=a.canonical_sha(tri),source_triangle_xyz_m=tri,replacement_triangles_xyz_m=new,source_area_m2=before,replacement_area_m2=after,lowered_area_m2=sum(g.area(q['polygon_xz_m'])for q in parts)))
 out['appended_surfaces']['road']=result;out['source_references']+= [ref(srcp),ref(pubp),ref(screenp),ref(Path(__file__)),ref(Path(p.__file__))];out['supersedes_patch']=ref(srcp);out['northern_junction_transition']=dict(profile=ref(screenp),physical_owners=ref(HERE/'physical_owners.json'),preserves_original_source_retirement_rows=True,physical_runtime='PENDING_EXACT_COMPOSED_SCENE_REPLAY');dump(HERE/'public_top_rebound.json',out);dump(HERE/'appended_top_retirement_ledger.json',dict(source=ref(srcp),output=ref(HERE/'public_top_rebound.json'),rows=ledger,index_map=source_map,maximum_area_partition_error_m2=maxerr,original_surface_edits_identical=out['surface_edits']==src['surface_edits'],other_material_arrays_identical=all(out['appended_surfaces'][m]==v for m,v in src['appended_surfaces'].items()if m!='road')))
 print('top',len(ledger),'triangles; logical',len(logical),'area',sum(r['lowered_area_m2']for r in ledger),'sec',time.monotonic()-start,flush=True)
 # Current actual scene only supplies measured neighbors and source-side provenance.
 sp=CITY/'evidence/r8_district_61_noble_r02_contracts_runtime/authored_scene.json';scene=json.loads(sp.read_bytes());print('scene',sha(sp),flush=True);idx=a.TriangleIndex(scene,[r['polygon_xz_m']for r in logical]);wp=CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r02/fields.json';water=json.loads(wp.read_bytes());outside=[dict(id=f['id']+':'+str(i),polygon_xz_m=t['polygon_xz_m'],plane_y_xz_m=t.get('plane_y_xz_m',a.common.plane(t['vertices_xyz_m'])))for f in water['profiles']for i,t in enumerate(f['triangles'])]
 bounds=side.interfaces(scene,idx,logical,outside);dump(HERE/'boundary_candidate.json',dict(sources=[ref(sp),ref(wp),ref(HERE/'physical_owners.json')],**bounds));print('boundary',{k:len(v)for k,v in bounds.items()if isinstance(v,list)},'sec',time.monotonic()-start,flush=True)

if __name__=='__main__':main()
