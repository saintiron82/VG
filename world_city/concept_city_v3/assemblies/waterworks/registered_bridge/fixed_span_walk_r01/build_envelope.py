"""Bounded continuous deck envelope over exact retained quarter-metre native treads.
All native collision, guard posts, rails, gantries and moving state pieces stay active.
"""
import json,pathlib,hashlib,math,numpy as np
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());BASE=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ref=lambda p:dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def write(p,v):
 with p.open('x')as f:json.dump(v,f,separators=(',',':'),allow_nan=False);f.write('\n')
def main():
 survey=json.loads((H/'native_tread_survey.json').read_bytes());native=ROOT/survey['native_render']['path'];assert sha(native)==survey['native_render']['sha256'];g=json.loads(native.read_bytes());candidate_path=BASE/'drawbridge_candidate/candidate.json';candidate=json.loads(candidate_path.read_bytes());pose=candidate['bridge_to_world'];B=np.array(pose['basis']);T=np.array(pose['translation']);all_x=np.array(survey['cell_grid_x']);all_z=np.array(survey['cell_grid_z']);floors=np.array([[np.nan if v is None else v for v in row]for row in survey['cell_top_heights']]);spans=[];triangles=[];mx=.112;my=.04
 for lo,hi,end0,end1 in [(-64.,-7.,1.75,4.),(7.,64.,4.,2.)]:
  xs=np.arange(lo,hi+.001,.25);zs=all_z;X,Z=np.meshgrid(xs,zs,indexing='ij');Y=np.full(X.shape,-np.inf);rects=[]
  for gi,group in enumerate(g['groups']):
   for qi,q in enumerate(group['quads']):
    a,b,c=np.array(q[:3]);n=np.cross(b-a,c-a)
    if n[1]<=0 or abs(n[0])+abs(n[2])>1e-10 or not(1.<=q[0][1]<=4.1):continue
    x0=max(lo,min(v[0]for v in q));x1=min(hi,max(v[0]for v in q));z0=max(-4.,min(v[2]for v in q));z1=min(4.,max(v[2]for v in q))
    if x1<=x0 or z1<=z0:continue
    y=q[0][1];dx=np.maximum(np.maximum(x0-X,X-x1),0);dz=np.maximum(np.maximum(z0-Z,Z-z1),0);Y=np.maximum(Y,y-mx*dx-my*dz);rects.append(dict(group_index=gi,quad_index=qi,bounds_xz_m=[x0,z0,x1,z1],floor_y_m=y))
  for x,y in [(lo,end0),(hi,end1)]:Y=np.maximum(Y,y-mx*np.abs(X-x))
  assert np.isfinite(Y).all();assert np.max(np.abs(Y[0]-end0))<1e-10,(lo,Y[0].tolist());assert np.max(np.abs(Y[-1]-end1))<1e-10,(hi,Y[-1].tolist())
  Y[0]=end0;Y[-1]=end1
  i0=int(round((lo-all_x[0])/.25));F=floors[i0:i0+len(xs)-1,:];assert np.isfinite(F).all();low=np.minimum.reduce([Y[:-1,:-1],Y[1:,:-1],Y[1:,1:],Y[:-1,1:]]);high=np.maximum.reduce([Y[:-1,:-1],Y[1:,:-1],Y[1:,1:],Y[:-1,1:]]);assert (low>=F-1e-10).all();embedding=float(np.max(high-F));gradmax=0.;first=len(triangles)
  for i in range(len(xs)-1):
   for j in range(len(zs)-1):
    quad=[[float(xs[k]),float(Y[k,l]),float(zs[l])]for k,l in[(i,j),(i+1,j),(i+1,j+1),(i,j+1)]]
    for inds in[(0,1,2),(0,2,3)]:
     local=np.array([quad[k]for k in inds]);u,v=local[1]-local[0],local[2]-local[0];n=np.cross(u,v);assert n[1]<0;gradient=math.hypot(n[0],n[2])/abs(n[1]);gradmax=max(gradmax,gradient);world=local@B.T+T;triangles.append(world.tolist())
  assert gradmax<=.12+1e-10,gradmax
  spans.append(dict(id='FIXED_NORTH'if lo<0 else'FIXED_SOUTH',native_local_x_interval_m=[lo,hi],native_local_z_interval_m=[-4,4],fixed_terminal_y_m=[end0,end1],xs_m=xs.tolist(),zs_m=zs.tolist(),heights_y_m=Y.tolist(),source_floor_rectangles=rects,maximum_triangle_gradient=gradmax,maximum_envelope_above_native_tread_m=embedding,minimum_envelope_above_native_tread_m=float(np.min(low-F)),triangles_range=[first,len(triangles)],full_width_native_cell_coverage=True))
 contract=dict(id='FIXED_BRIDGE_STONE_SPANS_CONTINUOUS_WALK_R01',disable_native_mesh_collider_ids=[],add_triangles_world_xyz_m=triangles,native_placement_id='BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED',native_source=ref(native),native_pose=pose,profile_source=ref(H/'native_tread_survey.json'),visible_geometry_unchanged=True,representation_kind='continuous_walk_over_retained_native_treads',triangle_convention='godot_clockwise_front',source_native_face_retirements=[],maximum_visible_tread_embedding_m=max(s['maximum_envelope_above_native_tread_m']for s in spans),maximum_gradient=max(s['maximum_triangle_gradient']for s in spans),logical_surface='Two continuous eight-metre carriage/walking bands over existing fixed stone spans. Original native collider remains active under the envelope and at all rails, posts, gantries and side edges.',limits=['Only local X[-64,-7] and [7,64], Z[-4,4] are covered. Central moving leaf, hinge covers and all moving barriers retain their source-state collision.','The outer sidewalk bands, side joins, live mechanism operation, carts and structural strength are not validated by this bounded contract.','Actual unchanged-controller replay against composed scene remains required.'])
 write(H/'profile.json',dict(schema='riverstone.fixed_native_span_continuous_envelope.v1',native_render=ref(native),native_candidate=ref(candidate_path),native_pose=pose,algorithm='Maximum anisotropic cone majorant of the exact native floor rectangles and four fixed full-width terminal lines. Per-axis Lipschitz bounds0.112/0.04 imply every emitted triangle grade≤sqrt(0.112²+0.04²). Every grid-cell corner is at or above its actual native tread.',source_floor_grid=ref(H/'native_tread_survey.json'),grade_bounds=[mx,my],spans=spans));write(H/'collision_contract.json',contract);write(H/'build_report.json',dict(status='SOURCE_ENVELOPE_CANDIDATE_RUNTIME_PENDING',profile=ref(H/'profile.json'),collision_contract=ref(H/'collision_contract.json'),triangles=len(triangles),native_face_retirements=0,maximum_gradient=contract['maximum_gradient'],maximum_visible_tread_embedding_m=contract['maximum_visible_tread_embedding_m'],spans=[{k:v for k,v in s.items()if k not in['xs_m','zs_m','heights_y_m','source_floor_rectangles']}for s in spans]));print(json.dumps(json.loads((H/'build_report.json').read_bytes()),indent=2))
if __name__=='__main__':main()
