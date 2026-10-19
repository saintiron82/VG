"""Finite measured northern bridge-to-main-gate approach, source candidate."""
import json,math
from pathlib import Path
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
HERE=Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if(p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3'
def write(name,data):(HERE/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def run():
 scene=a.load_scene();frame=scene['bridge_mechanism']['bridge_to_world'];b,t=frame['basis'],frame['translation'];world=lambda p:[t[i]+sum(b[i][j]*p[j]for j in range(3))for i in range(3)];local=lambda p:[sum(b[j][i]*(p[j]-t[j])for j in range(3))for i in range(3)]
 corners=[world([x,0,z])for x in[-112,-62]for z in[-6,6]];window=[[min(p[0]for p in corners),min(p[2]for p in corners)],[max(p[0]for p in corners),min(p[2]for p in corners)],[max(p[0]for p in corners),max(p[2]for p in corners)],[min(p[0]for p in corners),max(p[2]for p in corners)]];ix=a.TriangleIndex(scene,[window]);xend=-106.;width=6.;knots={-3.,3.};records=[]
 for row in ix.rows:
  tri=[local(v)for v in row['vertices_xyz_m']];zs=[]
  for u,v in zip(tri,tri[1:]+tri[:1]):
   if(u[0]-xend)*(v[0]-xend)<=0 and abs(v[0]-u[0])>1e-12:
    f=(xend-u[0])/(v[0]-u[0]);z=u[2]+f*(v[2]-u[2]);zs.append(z)
  if len(zs)>=2:
   lo,hi=max(-3.,min(zs)),min(3.,max(zs))
   if hi>lo+1e-9:records.append((lo,hi,row));knots.update([lo,hi])
 # Collapse source-edge intersections that describe one geometric knot.
 # This changes topology normalization, not seam/height acceptance tolerance.
 raw_knots=sorted(knots);knots=[]
 for z in raw_knots:
  if not knots or z-knots[-1]>1e-7:knots.append(z)
 sections=[];edge=[]
 for z in knots:
  hits=[r for lo,hi,r in records if lo-1e-7<=z<=hi+1e-7];p=world([xend,0,z]);ys=[a.common.height(r['plane_y_xz_m'],[p[0],p[2]])for r in hits]
  if not ys or max(ys)-min(ys)>1e-6:raise ValueError(('Nonmatching public seam',z,ys))
  if any(r['material']not in('road','alley')for r in hits):raise ValueError('Public seam not road owned')
  edge.append([xend,sum(ys)/len(ys),z])
 gate=next(p for p in scene['common_instances']if p['id']=='FORT_GATE:GATE_MAIN_BRIDGE_17');gp=gate['position_m'];g=local([gp[0],2.5,gp[2]]);yaw=gate['yaw_rad'];gx=[math.cos(yaw),0,-math.sin(yaw)]
 # Side orientation agrees with bridge local +Z (approximately world -X).
 if sum(gx[i]*b[i][2]for i in range(3))<0:gx=[-v for v in gx]
 gate_section=[local([gp[i]+gx[i]*z if i!=1 else 2.5 for i in range(3)])for z in knots]
 sections=[edge]+[[[x,y,z]for z in knots]for x,y in[(-102,1.9),(-98,2.3)]]+[gate_section]+[[[x,1.75,z]for z in knots]for x in[-72,-64]]
 triangles=[]
 for i,(u,v)in enumerate(zip(sections,sections[1:])):
  for j,j1 in ([(j,j+1)for j in range(len(knots)-1)]if i==0 else[(0,len(knots)-1)]):
   for k,tri in enumerate([[u[j],v[j],v[j1]],[u[j],v[j1],u[j1]]]):
    p=[world(q)for q in tri];coeff=a.common.plane(p);grade=math.hypot(*coeff[:2]);triangles.append(dict(id=f'NORTH_CONNECTOR:{i}:{j}:{k}',triangle_local_xyz_m=tri,triangle_xyz_m=p,plane_world_y_xz_m=coeff,maximum_grade=grade))
 result=dict(schema='riverstone.north_approach_r03.measured_profile.v1',status='CANDIDATE_REQUIRES_NATIVE_TERRAIN_SUPPORT_AND_REPLAY',base_scene_sha256=a.SCENE_SHA256,bridge_frame=frame,road_seam_local_x=xend,road_seam_source_triangles=sorted(set((r['material'],r['triangle_index'])for lo,hi,r in records)),cross_section_knots_local_z_m=knots,sections_local_xyz_m=sections,sections_world_xyz_m=[[world(p)for p in s]for s in sections],triangles=triangles,clear_width_m=width,main_gate_id=gate['id'],main_gate_local_center=g,maximum_grade=max(r['maximum_grade']for r in triangles),native_start_local_x=-64.,native_end_matching_y_m=1.75,gate_floor_y_m=2.5,geometry_scope='Old source road gap between fixed native north approach and main gate. Actual bridge native terminal and actual public terrain seam, not source-centerline hint.',limits=['City road graph continuation and gate clearance pending.','A supported native approach volume and finite source ownership are required; this mathematical profile is not an invisible unsupported ramp.'])
 write('profile.json',result);print(json.dumps({k:result[k]for k in['maximum_grade','clear_width_m','main_gate_local_center','native_start_local_x']})+' triangles='+str(len(triangles)));assert result['maximum_grade']<=.12+1e-8
if __name__=='__main__':run()
