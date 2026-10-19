"""Strict finite visible/collision sidecars; no hidden support generation."""
import hashlib,json,pathlib,numpy as np
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
RUNTIME='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2';AUTHORED='29466dbc33d5926895c236e2f62f6a1f7554614a5f794cb37571555baff27d85'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def resolve(r):
 p=pathlib.Path(r['path']);p=p if p.is_absolute()else ROOT/p;assert sha(p)==r['sha256'],'Changed external source';return p

def validate(a,p):
 assert a['schema']=='riverstone.explicit_visible_collision_addendum.v1'and a['id']=='CASTLE_GATE_SILL_VISIBLE_COLLISION_R01'
 assert a['base_scene']['sha256']==RUNTIME and p['base_scene_sha256']==RUNTIME
 assert not a['native_colliders_disabled']and not a['removed_source_triangles']and not p['surface_edits']and not p['removed_foundation_proxy_ids']and not p['source_surface_hashes']
 assert a['material']=='ground_stone'and set(p['appended_surfaces'])=={'ground_stone'}
 vs=a['visual_triangles_xyz_m'];cs=a['collision_triangles_xyz_m'];assert len(vs)==len(cs)==2 and sum(vs,[])==p['appended_surfaces']['ground_stone']
 assert cs==[[t[0],t[2],t[1]]for t in vs],'Visual/collision geometry mismatch'
 for typ,triangles in [(1,vs),(-1,cs)]:
  for t in triangles:
   assert all(v[1]==24 for v in t)and all(np.isfinite(v).all()for v in t)
   for dtype in [np.float64,np.float32]:
    q=np.asarray(t,dtype=dtype);assert typ*np.cross(q[1]-q[0],q[2]-q[0])[1]>0,'Wrong winding or degenerate triangle'
 domains=a['finite_domain_polygons_xz_m'];assert len(domains)==1 and domains[0]==p['ownership']['polygon_xz_m'];domain=domains[0];assert len(domain)==4
 def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 signs=[cross(domain[i],domain[(i+1)%4],domain[(i+2)%4])for i in range(4)];assert all(x>0 for x in signs)or all(x<0 for x in signs),'Nonconvex domain'
 triangles=[[(v[0],v[2])for v in t]for t in vs];assert set(sum(triangles,[]))==set(map(tuple,domain));assert len(set(triangles[0])&set(triangles[1]))==2
 area=abs(sum(domain[i][0]*domain[(i+1)%4][1]-domain[(i+1)%4][0]*domain[i][1]for i in range(4)))/2;tri_area=sum(abs(cross(*t))/2 for t in triangles);assert abs(area-tri_area)<1e-10 and abs(tri_area-1.5)<1e-10
 q=[a['support_control_xyz_m'][0],a['support_control_xyz_m'][2]];inside=[cross(domain[i],domain[(i+1)%4],q)for i in range(4)];assert all(x>=-1e-10 for x in inside)or all(x<=1e-10 for x in inside);assert a['support_control_xyz_m'][1]==24
 return dict(id=a['id'],add_triangles_world_xyz_m=cs,disable_native_mesh_collider_ids=[])
def load(manifest,authored_sha):
 assert authored_sha==AUTHORED;m=json.loads(manifest.read_bytes());assert m['authored_base_scene_sha256']==AUTHORED and m['runtime_base_scene_sha256']==RUNTIME;assert len(m['addenda'])==1;refs={'explicit_addenda_manifest':dict(path=str(manifest.resolve()),sha256=sha(manifest))};out=[]
 for i,source in enumerate(m['addenda']):
  path=resolve(source);a=json.loads(path.read_bytes());patch=resolve(a['source_surface_patch']);base=resolve(a['base_scene']);resolve(a['source_clearance_proof']);out.append(validate(a,json.loads(patch.read_bytes())))
  for name,p in [('sidecar',path),('visible_patch',patch),('base_runtime',base)]:refs['explicit_addendum:'+str(i)+':'+name]=dict(path=str(p),sha256=sha(p))
 return out,refs
