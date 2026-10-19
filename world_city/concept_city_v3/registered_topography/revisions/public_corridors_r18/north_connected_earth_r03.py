"""Recover one bounded dry component from the pre-bridge-mask terrain source."""
import json,math,time,collections
from .height_field import HERE
from . import finite_geometry_r03 as g
from .revise_native_emission_r07 import fan,ref
from ..r17_district_batches import author as a
from ..r02_assembly_overlay import author as original

def main():
 start=time.monotonic();cp=HERE/'north_residual_components_r01.json';d=json.loads(cp.read_bytes());groups=[r for r in d['components']if r['matching_unknown_edges']];assert len(groups)==1;component=groups[0];masks=component['polygons_xz_m'];owners=[];raw=[];covered=[];maxgrade=0.;source_refs=[ref(cp),ref(__import__('pathlib').Path(original.__file__)),ref(__import__('pathlib').Path(original.previous.__file__)),ref(__import__('pathlib').Path(original.previous.base.__file__))]
 bb=component['bounds_xz_m'];sx=math.floor(bb[0]/4)*4;sz=math.floor(bb[1]/4)*4;ex=math.ceil(bb[2]/4)*4;ez=math.ceil(bb[3]/4)*4
 for x in range(sx,ex,4):
  for z in range(sz,ez,4):
   cell=[x,z,x+4,z+4];records=original.surface_domains(cell)
   for ri,r in enumerate(records):
    if not r.get('render_land',True):continue
    p=g.normalize_mask(r['polygon_xz_m']);v=[[u,original.surface_height_at(r,u,w),w]for u,w in p]
    for ti in range(1,len(v)-1):
     t=[v[0],v[ti],v[ti+1]]
     if abs(a.normal_y(t))<=1e-14:continue
     if a.normal_y(t)<0:t=[t[0],t[2],t[1]]
     plane=a.common.plane(t);poly=[[q[0],q[2]]for q in t]
     for mi,m in enumerate(masks):
      if not a.intersects(a.bounds(poly),a.bounds(m)):continue
      q=g.clip(poly,m)
      if not q:continue
      id=f'NORTH_PREMASK_EARTH:{x}:{z}:{ri}:{ti}:{mi}';out=dict(id=id,polygon_xz_m=q,plane_y_xz_m=plane,triangles_xyz_m=fan(q,plane),source_owner_id=r['owner_id'],source_kind=r['kind'],source_cell_bounds_xz_m=cell,source_triangle_xyz_m=t,source_owner_record=r,material='ground_earth',action='field',kind='finite_premask_nonwalking_earth_restoration');owners.append(out);covered.append(q);maxgrade=max(maxgrade,math.hypot(*plane[:2]))
 uncovered=g.subtract(masks,covered);area=math.fsum(g.area(q)for q in masks);rendered=math.fsum(g.area(q)for q in covered);ua=math.fsum(g.area(q)for q in uncovered)
 sp=a.CITY/'evidence/r8_district_r04/scene.json';scene=json.loads(sp.read_bytes());idx=a.TriangleIndex(scene,masks);hits=[]
 for r in owners:
  for i in idx.index.candidates(r['polygon_xz_m']):
   s=idx.rows[i];q=g.clip(r['polygon_xz_m'],s['polygon_xz_m']);ar=g.area(q)
   if ar>1e-10:hits.append(dict(id=r['id'],source_material=s['material'],source_triangle_index=s['triangle_index'],area_m2=ar))
 out=dict(schema='riverstone.r18.bounded_premask_earth_restore.v1',status='SOURCE_GEOMETRY_CANDIDATE_PENDING_OUTER_SEAMS',source_refs=source_refs+[ref(sp),ref(__import__('pathlib').Path(__file__))],component=component,physical_earth_owners=owners,source_area_m2=area,rendered_area_m2=rendered,uncovered_area_m2=ua,uncovered_polygons_xz_m=uncovered,positive_overlap_current_terrain=hits,maximum_source_triangle_grade=maxgrade,seconds=time.monotonic()-start,activation=False,policy='Only the dry connected component incident to the three current unknown edges. Source finite4m owner cells are evaluated before obsolete native-bridge masking; clipped points remain on those source triangle planes. No R18-road-plane extrapolation, other legacy components or water fill. Outer/native side closure remains required.')
 op=HERE/'north_connected_earth_r03_candidate.json';op.write_text(json.dumps(out,separators=(',',':'))+'\n');print({k:v for k,v in out.items()if k in ['source_area_m2','rendered_area_m2','uncovered_area_m2','positive_overlap_current_terrain','maximum_source_triangle_grade','seconds']},len(owners),ref(op))
if __name__=='__main__':main()
