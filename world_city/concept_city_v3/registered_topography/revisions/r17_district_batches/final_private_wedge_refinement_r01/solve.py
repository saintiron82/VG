import json,types,time,math
from pathlib import Path
from .. import author as a
from ..bounded_profile_r01 import finite
from ..contour_bulk_r01 import profile_mesh
from ..final_profile_audit_r01.exact_clip import half
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
SOURCE=a.HERE/'final_district_profiles_r02/BLOCK_001_R8_C003.json'
KNOT=[-161.1724023277206,-101.17240232772062];END=[KNOT[0]+1,KNOT[1]+1]
def run():
 d=json.loads(SOURCE.read_bytes());c=d['candidate'];splits=[]
 def grid_parts(domains,regions,pitch):
  parts,cells=profile_mesh.grid_parts(domains,regions,pitch);out=[]
  for i,p in enumerate(parts):
   if finite.inside(KNOT,p,1e-8):
    left=half(p,KNOT,END,1,True);right=half(p,KNOT,END,1,False)
    if a.geo.polygon_area(left)>1e-12 and a.geo.polygon_area(right)>1e-12:
     assert abs(a.geo.polygon_area(p)-a.geo.polygon_area(left)-a.geo.polygon_area(right))<1e-10
     splits.append(dict(original_part_index=i,original_polygon_xz_m=p,split_polygons_xz_m=[left,right]));out.extend([left,right]);continue
   out.append(p)
  return out,cells
 mesh=types.SimpleNamespace(**vars(profile_mesh));mesh.grid_parts=grid_parts;solver=types.FunctionType(finite.solve.__code__,dict(finite.solve.__globals__,profile_mesh=mesh),argdefs=finite.solve.__defaults__)
 result=solver(d['private_domain_polygons_xz_m'],d['court_fixed_regions']+d['public_fixed_regions'],lambda p:c['floor_y_m'],pitch=1.,limit=.25,seam_points=[p for r in d['court_fixed_regions']+d['public_fixed_regions']for p in r['polygon_xz_m']]);out=dict(d,result=result,local_refinement=dict(shared_public_knot_xz_m=KNOT,shared_public_line_point_xz_m=END,source_public_ids=['R18_FINITE:12799:0','R18_FINITE:12800:0'],splits=splits),prior_profile=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=a.sha(SOURCE)),design_policy='Explicit pedestrian stepped entry with continuous collision envelope, no cart-access claim',grade_limit=.25,activation=False);write(HERE/'BLOCK_001_R8_C003.json',out);print(result['status'],result.get('maximum_gradient'),'splits',len(splits))
if __name__=='__main__':run()
