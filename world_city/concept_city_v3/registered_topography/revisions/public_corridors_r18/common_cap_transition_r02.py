"""Finite planar upper envelope joining the actual retained common cap at Y8.
Native cap domains stay excluded. Raised public pieces meet each old plane on
its exact equality line; no independent resampling of that exterior seam.
"""
import json,math,time
from .height_field import HERE,fixed_sources
from . import finite_geometry_r03 as g
from .emit_finite_cells import positive_fan
from ..r17_district_batches import author as a
LIMIT=.12

def half_linear(p,coef,positive=True):
 if not p:return[]
 out=[];u=p[-1];du=coef[0]*u[0]+coef[1]*u[1]+coef[2];iu=du>=0 if positive else du<=0
 for v in p:
  dv=coef[0]*v[0]+coef[1]*v[1]+coef[2];iv=dv>=0 if positive else dv<=0
  if iu!=iv:
   f=du/(du-dv);out.append([u[k]+f*(v[k]-u[k])for k in(0,1)])
  if iv:out.append(v)
  u,du,iu=v,dv,iv
 return g.clean(out)
def difference_plane(a,b):return[a[k]-b[k]for k in range(3)]

def main():
 start=time.monotonic();source=HERE/'finite_field_candidate_r02.json';data=json.loads(source.read_bytes());path=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/common_entry_repair_r03/actual_outer_cap_public_handoff.json';assert a.sha(path)=='489bae744aa9a6844454355366eaf9d14b8a238d49826f687c1c214c7f7f8676';cap=json.loads(path.read_bytes());caps=cap['native_cap_polygon_parts_xz_m'];bounds=a.bounds([p for poly in caps for p in poly]);b=[bounds[0]-16,bounds[1]-16,bounds[2]+16,bounds[3]+16];box=[[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]];roof=[]
 for i,p in enumerate(caps):
  x0,z0,x1,z1=a.bounds(p);planes=[[0,0,8],[LIMIT,0,8-LIMIT*x0],[-LIMIT,0,8+LIMIT*x1],[0,LIMIT,8-LIMIT*z0],[0,-LIMIT,8+LIMIT*z1]]
  for j,pl in enumerate(planes):
   domain=box
   for other in planes:domain=half_linear(domain,difference_plane(other,pl))
   if domain:roof.append(dict(id=f'COMMON_ACTUAL_CAP:{i}:{j}',polygon_xz_m=domain,plane_y_xz_m=pl))
 roof += [dict(r,id=r['id']+':UPPER',plane_y_xz_m=[-r['plane_y_xz_m'][0],-r['plane_y_xz_m'][1],16-r['plane_y_xz_m'][2]],upper=True)for r in list(roof)]
 output=[];ledger=[];removed_native=[];regions,segments,refs=fixed_sources();fixed_ix=a.geo._SpatialIndex(8)
 for i,r in enumerate(regions):fixed_ix.add(i,r['polygon_xz_m'])
 fixed_conflicts=[];outer_contacts=[]
 for record in data['records']:
  p=record['polygon_xz_m'];bb=a.bounds(p)
  if bb[2]<b[0]or bb[0]>b[2]or bb[3]<b[1]or bb[1]>b[3]:output.append(record);continue
  cap_parts=g.subtract([p],caps);removed=g.area(p)-math.fsum(g.area(q)for q in cap_parts)
  if removed>1e-12:removed_native.append(dict(source_owner_id=record['id'],removed_area_m2=removed))
  pieces=[dict(record,polygon_xz_m=q,triangles_xyz_m=positive_fan(q,record['plane_y_xz_m']))for q in cap_parts]
  for roof_record in roof:
   new=[];mask=roof_record['polygon_xz_m'];pl=roof_record['plane_y_xz_m']
   for piece in pieces:
    q=g.clip(piece['polygon_xz_m'],mask)
    if not q:new.append(piece);continue
    coef=difference_plane(piece['plane_y_xz_m'],pl)if roof_record.get('upper')else difference_plane(pl,piece['plane_y_xz_m']);raised=half_linear(q,coef)
    if not raised or max(a.common.height(coef,v)for v in raised)<=1e-12:new.append(piece);continue
    for q0 in g.subtract([piece['polygon_xz_m']],[raised]):new.append(dict(piece,polygon_xz_m=q0,triangles_xyz_m=positive_fan(q0,piece['plane_y_xz_m'])))
    new.append(dict(piece,polygon_xz_m=raised,plane_y_xz_m=pl,triangles_xyz_m=positive_fan(raised,pl),source_gradient=LIMIT if pl[:2]!=[0,0]else 0.,common_cap_source_id=roof_record['id']))
   pieces=new
  changed=[r for r in pieces if r.get('common_cap_source_id')]
  if changed:
   for j,piece in enumerate(pieces):piece['id']=record['id']+':COMMON:'+str(j)
   for r in changed:
    q=r['polygon_xz_m'];pl=r['plane_y_xz_m'];delta=max(a.common.height(pl,v)-a.common.height(record['plane_y_xz_m'],v)for v in q)
    if any(abs(v[0]-b[0])<1e-8 or abs(v[0]-b[2])<1e-8 or abs(v[1]-b[1])<1e-8 or abs(v[1]-b[3])<1e-8 for v in q):outer_contacts.append(r['id'])
    for n in fixed_ix.candidates(q):
     inter=g.clip(q,regions[n]['polygon_xz_m'])
     if inter and max(abs(a.common.height(pl,v)-a.common.height(regions[n]['plane_y_xz_m'],v))for v in inter)>1e-7:fixed_conflicts.append(dict(id=r['id'],fixed_id=regions[n]['id'],polygon_xz_m=inter))
    ledger.append(dict(id=r['id'],source_owner_id=record['id'],polygon_xz_m=q,plane_y_xz_m=pl,previous_plane_y_xz_m=record['plane_y_xz_m'],max_raise_m=delta,max_abs_change_m=max(abs(a.common.height(pl,v)-a.common.height(record['plane_y_xz_m'],v))for v in q),area_m2=g.area(q)))
  output+=pieces
 report=dict(status='COMMON_CAP_FINITE_CANDIDATE'if not(fixed_conflicts or outer_contacts)else'HELD_COMMON_CAP_BOUNDARY_OR_FIXED_CONFLICT',source_candidate=dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source)),actual_cap_handoff=dict(path=str(path.relative_to(a.ROOT)),sha256=a.sha(path)),maximum_roof_gradient=LIMIT,changed_parts=len(ledger),changed_area_m2=math.fsum(r['area_m2']for r in ledger),max_raise_m=max((r['max_raise_m']for r in ledger),default=0),max_absolute_height_change_m=max((r['max_abs_change_m']for r in ledger),default=0),removed_native_cap_area_m2=math.fsum(r['removed_area_m2']for r in removed_native),supplemental_native_exclusions=[dict(id='COMMON_R03_ACTUAL_CAP:'+str(i),polygon_xz_m=p)for i,p in enumerate(caps)],finite_screen_bounds_xz_m=b,outer_screen_contacts=outer_contacts,fixed_conflicts=fixed_conflicts,owner_area_delta_m2=math.fsum(g.area(r['polygon_xz_m'])for r in output)-math.fsum(g.area(r['polygon_xz_m'])for r in data['records']),seconds=time.monotonic()-start,activation=False)
 data['report']['common_cap_transition']=report;data['records']=output
 data['report']['finite_records']=len(output);data['report']['finite_area_m2']=math.fsum(g.area(r['polygon_xz_m'])for r in output);data['report']['rendered_triangles']=sum(len(r['triangles_xyz_m'])for r in output);data['report']['rendered_area_m2']=math.fsum(abs(a.normal_y(t))/2 for r in output for t in r['triangles_xyz_m']);data['report']['owner_minus_rendered_area_m2']=data['report']['finite_area_m2']-data['report']['rendered_area_m2'];data['report']['empty_fan_records']=[dict(id=r['id'],area_m2=g.area(r['polygon_xz_m']))for r in output if not r['triangles_xyz_m']]
 (HERE/'finite_field_candidate_r04_common.json').write_text(json.dumps(data,separators=(',',':'))+'\n');(HERE/'common_cap_transition_review_r02.json').write_text(json.dumps(dict(report=report,changed_parts=ledger),separators=(',',':'))+'\n');print(report,flush=True)
if __name__=='__main__':main()
