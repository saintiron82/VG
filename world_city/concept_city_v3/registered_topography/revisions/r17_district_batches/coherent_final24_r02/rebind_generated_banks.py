"""Exact producer-row retirement of later banks in the same final23 domains."""
import json,time
from .prepare import HERE,write,ref,load
from .. import author as a,side_clearance
from ..contour_bulk_r01 import compose_districts as c

def run():
 start=time.monotonic();request=json.loads((HERE/'accepted_source_request.json').read_bytes());binding=request['current_main_binding'];source=load(binding);hand=json.loads((HERE/'physical_owner_handoff_r02.json').read_bytes());owners=hand['physical_earth_owners'];index=a.geo._SpatialIndex(4)
 for i,r in enumerate(owners):index.add(i,r['polygon_xz_m'])
 replacements=[];ledger=[];(HERE/'producer_rebindings').mkdir(exist_ok=True)
 for pi,b in enumerate(source['patches']):
  patch=load(b);vertices=patch.get('appended_surfaces',{}).get('bank',[])
  if not vertices:continue
  sideidx=side_clearance.SideIndex(dict(surfaces={'bank':vertices}),[r['polygon_xz_m']for r in owners]);changed={};rows=[]
  for r in sideidx.rows:
   remaining=[r['vertices_xyz_m']];removed=[]
   for j in sorted(index.candidates(r['projection_xz_m'])):
    parts=[]
    for p in remaining:
     outer,inner=c.subtract_side(p,owners[j]['polygon_xz_m']);parts.extend(outer)
     if inner:removed.append(inner)
    remaining=parts
    if not remaining:break
   area=sum(side_clearance.area3d(p)for p in removed)
   if area<1e-9:continue
   triangles=[[p[0],p[k],p[k+1]]for p in remaining for k in range(1,len(p)-1)];before=side_clearance.area3d(r['vertices_xyz_m']);after=sum(side_clearance.area3d(t)for t in triangles);assert abs(before-after-area)<1e-6
   changed[r['triangle_index']]=triangles;rows.append(dict(producer_index=pi,producer=b,appended_material='bank',appended_triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],source_vertices_xyz_m=r['vertices_xyz_m'],replacement_triangles_xyz_m=triangles,removed_area_m2=area,remaining_area_m2=after))
  if not rows:continue
  new=[]
  for i in range(len(vertices)//3):new.extend(v for tr in changed.get(i,[vertices[i*3:i*3+3]])for v in tr)
  derived=dict(patch,appended_surfaces=dict(patch['appended_surfaces'],bank=new),final23_bank_retirement=dict(source_producer=b,source_main_binding=binding,physical_owner_handoff=ref(HERE/'physical_owner_handoff_r02.json'),edited_source_rows=len(rows),policy='Only finite intersections with final23 physical ownership are retired; all other producer values and row order are preserved.'))
  path='producer_rebindings/producer_'+str(pi).zfill(2)+'.json';write(path,derived);replacements.append(dict(producer_index=pi,original=b,replacement=ref(HERE/path)));ledger.extend(rows);print('Producer',pi,'bounded bank rows',len(rows),flush=True)
 write('generated_bank_source_ledger_r01.json',dict(source_main_binding=binding,producer_replacements=replacements,rows=ledger,summary=dict(producers=len(replacements),source_rows=len(ledger),removed_area_m2=sum(r['removed_area_m2']for r in ledger),elapsed_s=time.monotonic()-start),activation=False));print('Complete generated banks',len(replacements),len(ledger),flush=True)
if __name__=='__main__':run()
