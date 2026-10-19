"""Separate grid-only interpolation failures from finite public remnants."""
import json,math,time,sys
from . import public_domain as d
from .grid_candidate import grade
from .survey import HERE
from ..r17_district_batches import author as a

def run():
 start=time.monotonic();input_name=sys.argv[1]if len(sys.argv)>1 else'field_tessellation.json';output_name=sys.argv[2]if len(sys.argv)>2 else'emitted_grade_diagnosis_r03.json';data=json.loads((HERE/input_name).read_bytes());traffic=d.polygons();ti=a.geo._SpatialIndex(8)
 for i,p in enumerate(traffic):ti.add(i,p)
 mask_path=HERE/'boundary_ownership_inputs_r01.json';cache=json.loads(mask_path.read_bytes());assert all(a.sha(a.ROOT/r['path'])==r['sha256']for r in cache['source_refs']);exclusions=cache['masks'];ei=a.geo._SpatialIndex(8)
 for i,r in enumerate(exclusions):ei.add(i,r['polygon_xz_m'])
 rows=[]
 for n,t in enumerate(data['triangles_xyz_m']):
  g=grade(t)
  if g<=.12+1e-7:continue
  p=[[v[0],v[2]]for v in t];hits=a.common.disjoint_union([q for j in ti.candidates(p)if(q:=a.clip(p,traffic[j]))]);retained=a.common.subtract(hits,[exclusions[j]['polygon_xz_m']for j in ei.candidates(p)]);area=a.geo.polygon_area(p);L=max(math.dist(u,v)for u,v in zip(p,p[1:]+p[:1]));rows.append(dict(triangle_index=n,triangle_xyz_m=t,gradient=g,area_m2=area,altitude_m=2*area/L,traffic_intersection_area_m2=sum(a.geo.polygon_area(q)for q in hits),after_known_exclusion_area_m2=sum(a.geo.polygon_area(q)for q in retained),retained_polygons_xz_m=retained))
 summary=dict(triangles=len(rows),total_bad_grid_area_m2=sum(r['area_m2']for r in rows),maximum_grade=max(r['gradient']for r in rows),traffic_bad_area_m2=sum(r['traffic_intersection_area_m2']for r in rows),remaining_after_known_exclusions_area_m2=sum(r['after_known_exclusion_area_m2']for r in rows),remaining_triangle_count=sum(r['after_known_exclusion_area_m2']>1e-10 for r in rows),remaining_maximum_grade=max((r['gradient']for r in rows if r['after_known_exclusion_area_m2']>1e-10),default=0),seconds=time.monotonic()-start)
 out=dict(source_mesh_sha256=a.sha(HERE/input_name),source_domain_refs=d.source_refs(),ownership_inputs_sha256=a.sha(mask_path),ownership_source_refs=cache['source_refs'],summary=summary,rows=rows,scope='Finite clipping against parent current exact all-pack/water ownership cache; this is not an activation.')
 (HERE/output_name).write_text(json.dumps(out,separators=(',',':'))+'\n');print(summary)
if __name__=='__main__':run()
