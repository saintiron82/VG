import json,math,struct,itertools
from .inspect_contacts import H,B,ref,norm,plane,height,distance,contains
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as g

def f32(v):return struct.unpack('f',struct.pack('f',v))[0]
def area3(t):
 u=[t[1][i]-t[0][i]for i in range(3)];v=[t[2][i]-t[0][i]for i in range(3)];return math.hypot(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])/2

def main():
 rows=[];sources=[]
 for route,window in [('BLOCK_002:R8_C009:PUBLIC_ENTRY',[24.7,-189.,28.7,-181.5]),('BLOCK_005:R8_C002:PUBLIC_ENTRY',[351.5,-55.1,357.5,-50.9])]:
  gp=B/'geometry'/f'{route}.json';geo=json.loads(gp.read_bytes());sources.append(ref(gp));faces=[]
  for i,t in enumerate(geo['triangles']):
   p=[[v[0],v[2]]for v in t];bb=[min(v[0]for v in p),min(v[1]for v in p),max(v[0]for v in p),max(v[1]for v in p)]
   if bb[2]<window[0]or bb[0]>window[2]or bb[3]<window[1]or bb[1]>window[3]:continue
   L=max(math.dist(u,v)for u,v in itertools.combinations(p,2));ar=g.area(p);width=2*ar/L if L else 0
   if not 0<width<=1e-9:continue
   q=[[f32(x)for x in v]for v in t];fq=[[v[0],v[2]]for v in q];fn=norm(q);dn=norm(t)
   faces.append(dict(extracted_triangle_index=i,scene_source_face=geo['source_face_indices'][i],triangle_godot_xyz_m=t,triangle_scene_xyz_m=[t[0],t[2],t[1]],triangle_float32_godot_xyz_m=q,projected_area_m2=ar,maximum_edge_m=L,minimum_altitude_m=width,shortest_edge_m=min(math.dist(u,v)for u,v in itertools.combinations(t,2)),float32_unique_vertices=len({tuple(v)for v in q}),float32_area3_m2=area3(q),float32_normal=fn,double_normal=dn,float32_winding_flipped=fn[1]*dn[1]<0,classification='EXACT_FLOAT32_COLLAPSE'if area3(q)==0 else'NEAR_ZERO_SOURCE_WIDTH_WITH_FLOAT32_ARTIFACT'))
  rows.append(dict(case_id=route,bounded_window_xz_m=window,faces=faces,total_source_area_m2=math.fsum(f['projected_area_m2']for f in faces),maximum_source_altitude_m=max(f['minimum_altitude_m']for f in faces)))
 out=dict(schema='riverstone.r18.runtime_precision_sliver_diagnostic.v1',status='EXACT_NUMERICAL_DEBRIS_CANDIDATE_PENDING_REMOVAL_ONLY_REPLAY',sources=sources,rows=rows,policy='Only bounded source faces with metric minimum altitude≤1nm are identified. No file or collision input is changed. Float32 calculations model the actual Vector3 representation; runtime causality still needs controlled replay.')
 p=H/'runtime_precision_slivers.json';p.write_text(json.dumps(out,separators=(',',':'))+'\n');print(ref(p));print([(r['case_id'],len(r['faces']),r['total_source_area_m2'],r['maximum_source_altitude_m'],sum(x['float32_area3_m2']==0 for x in r['faces']))for r in rows])
if __name__=='__main__':main()
