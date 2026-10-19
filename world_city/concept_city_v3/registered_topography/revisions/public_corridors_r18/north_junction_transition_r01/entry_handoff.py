import json,math
from .author import HERE,CITY,ROOT,g,p,a,ref,dump

def main():
 src=CITY/'assemblies/ordinary/registered/district_fabric_r01/b05_native_junction_entry_r04/source_candidates.json';d=json.loads(src.read_bytes());candidate=d['candidates'][0];route=g.union(candidate['polygons_xz_m']);localp=HERE/'physical_owners.json';local=json.loads(localp.read_bytes());pubp=HERE.parent/'finite_field_candidate_r07_native_bound.json';public=json.loads(pubp.read_bytes());wp=CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r02/fields.json';water=json.loads(wp.read_bytes());replaced=set(local['replaced_source_owner_ids']);rows=local['records']+[r for r in public['records']if r['id']not in replaced]+[dict(id=f['id']+':'+str(i),polygon_xz_m=t['polygon_xz_m'],plane_y_xz_m=t.get('plane_y_xz_m',a.common.plane(t['vertices_xyz_m'])),kind='accepted_water_approach')for f in water['profiles']for i,t in enumerate(f['triangles'])];idx=a.geo._SpatialIndex(4)
 for i,r in enumerate(rows):idx.add(i,r['polygon_xz_m'])
 out=[]
 for ri,poly in enumerate(route):
  claimed=[]
  for i in sorted(idx.candidates(poly)):
   r=rows[i];q=g.clip(poly,r['polygon_xz_m'])
   if not q:continue
   for part in g.subtract([q],claimed):out.append(dict(id='C006_PUBLIC:'+str(len(out)),source_owner_id=r['id'],polygon_xz_m=part,plane_y_xz_m=r['plane_y_xz_m'],kind=r.get('kind','retained_public'),source_route_union_piece=ri));claimed.append(q)
 result=dict(schema='riverstone.exact_entry_public_planes.v1',status='CANDIDATE_PUBLIC_PROFILE_PENDING_LOCAL_SIDE_SEAL_AND_RUNTIME',sources=[ref(src),ref(localp),ref(pubp),ref(wp)],holding_id=candidate['holding_id'],candidate_index=0,source_polyline_xz_m=candidate['polyline_xz_m'],floor_y_m=candidate['floor_y_m'],public_overlap_records=out,public_overlap_area_m2=sum(g.area(r['polygon_xz_m'])for r in out),maximum_public_grade=max(math.hypot(*r['plane_y_xz_m'][:2])for r in out));print(dump(HERE/'c006_public_planes.json',result));print(len(out),result['public_overlap_area_m2'],result['maximum_public_grade'])
if __name__=='__main__':main()
