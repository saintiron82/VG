"""Partition final continuous private profiles into native and finite ground collars."""
from pathlib import Path
import sys,json,argparse,importlib.util,copy,time,math
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE))
from resolve_pack import *
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg
OUT=Path(__file__).resolve().parent;OLD=OUT.with_name('noble_entry_batch_r01')
spec=importlib.util.spec_from_file_location('old_ground',OLD/'build_ground_patch.py');oldground=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldground)
spec=importlib.util.spec_from_file_location('finite_collision_helper',OUT.parent/'common_entry_repair_r03/candidate_r02/author_collision.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
sys.path.insert(0,str(OUT))
from finite_collision_clip import cutprism as disjoint_cutprism

def write(name,obj):p=OUT/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(obj,indent=2)+'\n');return ref(p)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--solutions',required=True);ap.add_argument('--inputs',default=str(OUT/'tail_solve_inputs.json'));ap.add_argument('--public-records',required=True);ap.add_argument('--owners',default='E1,E2,E3,E4,E5,E6,E7');args=ap.parse_args();pack=load(OUT/'resolved_native_candidate.json');inputs=load(Path(args.inputs).resolve());publicpath=Path(args.public_records).resolve();public=load(publicpath)['records'];pi=geo._SpatialIndex(4)
 for i,r in enumerate(public):pi.add(i,r['polygon_xz_m'])
 caprecords=load(CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json')['records'];capby={r['property_id']:[c['polygon_xz_m']for c in r['candidate_columns']]for r in caprecords};rows=[];allcollars=[]
 for owner in pack['owners']:
  eid=owner['owner_id']
  if eid not in args.owners.split(','):continue
  entry=next(r for r in inputs['owners']if r['owner_id']==eid);fine=next(p for p in pack['placements']if p['owner_id']==eid and p['role']=='fine_access');base=next(p for p in pack['placements']if p['owner_id']==eid and p['role']=='retained_base');old=load(OLD/f'geometry/{eid}_physical_top.json');tops=oldground.upper(oldground.faces(fine)[0]);basepolys=[r['polygon_xz_m']for r in oldground.faces(base)[0]];ni=geo._SpatialIndex(4)
  for i,r in enumerate(tops):ni.add(i,r['polygon_xz_m'])
  if eid=='E3':field=copy.deepcopy(old['top_pieces']);proposalref=None
  else:
   proposalpath=Path(args.solutions).resolve()/(eid+'_proposal.json');proposal=load(proposalpath);solved=proposal['result'].get('result',proposal['result']);assert solved['status']=='PASSED_FINITE_TRIANGLE_GRADE';proposalref=ref(proposalpath);field=[]
   for r in old['top_pieces']:
    for q in fg.subtract([r['polygon_xz_m']],[entry['window_polygon_xz_m']]):
     if fg.area(q)>1e-12:field.append(dict(r,polygon_xz_m=q))
   field +=[dict(polygon_xz_m=t['polygon_xz_m'],plane_y_xz_m=t['plane_y_xz_m'])for t in solved['triangles']if fg.area(t['polygon_xz_m'])>1e-12]
  nativephysical=[];collars=[];errors=[];publiccontacts=[]
  for r in field:
   p=r['polygon_xz_m'];pubmasks=[public[j]['polygon_xz_m']for j in pi.candidates(p)if fg.clip(p,public[j]['polygon_xz_m'])];parts=fg.subtract([p],pubmasks+capby.get(eid,[]))
   for part in parts:
    covers=[]
    for j in ni.candidates(part):
     q=fg.clip(part,tops[j]['polygon_xz_m'])
     if not q:continue
     covers.append(q);nativephysical.append(dict(polygon_xz_m=q,plane_y_xz_m=r['plane_y_xz_m'],native_face_id=tops[j]['id']));dy=[tops[j]['plane_y_xz_m'][2]-terrain.common.height(r['plane_y_xz_m'],v)for v in q];errors.append(dict(native_face_id=tops[j]['id'],polygon_xz_m=q,minimum_native_above_collision_m=min(dy),maximum_native_above_collision_m=max(dy)))
    for q in fg.subtract([part],covers+basepolys):
     if fg.area(q)>1e-10:collars.append(dict(id='R02_NOBLE_PRIVATE_COLLAR:'+eid+':'+str(len(collars)),owner_id=eid,polygon_xz_m=q,plane_y_xz_m=r['plane_y_xz_m'],material='ground_stone',kind='finite_public_priority_sampling_collar'))
  for r in tops:
   for j in pi.candidates(r['polygon_xz_m']):
    q=fg.clip(r['polygon_xz_m'],public[j]['polygon_xz_m'])
    if fg.area(q)>1e-10:publiccontacts.append(dict(native_face_id=r['id'],public_id=public[j]['id'],polygon_xz_m=q,area_m2=fg.area(q)))
  assert not publiccontacts,(eid,'actual native overlaps public',sum(r['area_m2']for r in publiccontacts));assert min(e['minimum_native_above_collision_m']for e in errors)>=-.0750001,(eid,min(e['minimum_native_above_collision_m']for e in errors));assert max(e['maximum_native_above_collision_m']for e in errors)<=.1500001,(eid,max(e['maximum_native_above_collision_m']for e in errors))
  native_risers=[];collar_risers=[]
  for riser in proposal['result'].get('vertical_risers',[])if eid!='E3'else[]:
   for tr in riser['triangles_xyz_m']:
    remaining=[tr];box=b.rect(min(v[0]for v in tr)-1e-7,min(v[2]for v in tr)-1e-7,max(v[0]for v in tr)+1e-7,max(v[2]for v in tr)+1e-7)
    for j in ni.candidates(box):
     nxt=[]
     for piece in remaining:
      outside,inside=disjoint_cutprism(piece,tops[j]['polygon_xz_m']);nxt+=outside
      if inside and helper.area3(inside)>1e-12:native_risers +=[[inside[0],inside[k],inside[k+1]]for k in range(1,len(inside)-1)]
     remaining=nxt
    for c in collars:
     nxt=[]
     for piece in remaining:
      outside,inside=disjoint_cutprism(piece,c['polygon_xz_m']);nxt+=outside
      if inside and helper.area3(inside)>1e-12:collar_risers +=[[inside[0],inside[k],inside[k+1]]for k in range(1,len(inside)-1)]
     remaining=nxt
  native_ref=write(f'geometry/{eid}_physical_top.json',dict(owner_id=eid,top_pieces=nativephysical,corridor_polygons_xz_m=old['corridor_polygons_xz_m'],route_points_xz_m=old['route_points_xz_m'],finite_tail_solve=proposalref));allcollars+=collars;row=dict(owner_id=eid,physical_top=native_ref,actual_native_upward_faces=tops,private_field_pieces=field,collar_pieces=collars,profile_native_envelope_errors=errors,private_grade_limit=solved['grade_limit']if eid!='E3'else.12,native_proxy_riser_triangles_xyz_m=native_risers,collar_riser_triangles_xyz_m=collar_risers,private_vertical_risers=proposal['result'].get('vertical_risers',[])if eid!='E3'else[],public_projection_contacts=publiccontacts,summary=dict(native_physical_area_m2=sum(fg.area(r['polygon_xz_m'])for r in nativephysical),collar_area_m2=sum(fg.area(r['polygon_xz_m'])for r in collars),max_native_above_physical_m=max(e['maximum_native_above_collision_m']for e in errors),max_physical_above_native_m=max(0,-min(e['minimum_native_above_collision_m']for e in errors))));rows.append(row);print(eid,row['summary'],flush=True)
 write('physical_profile_audit.json',dict(owners=rows,public_source=ref(publicpath),native_source=ref(OUT/'resolved_native_candidate.json'),runtime_ready=False));write('private_collars.json',dict(owners=allcollars,source_native=ref(OUT/'resolved_native_candidate.json'),public_source=ref(publicpath),runtime_ready=False))
if __name__=='__main__':main()
