"""Collision-order correction only. Native visuals and world profile unchanged."""
import copy,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=next(p for p in HERE.parents if(p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3'
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def ny(t):
 a,b,c=t;return(b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2])
def run():
 old=json.loads((BASE/'collision_contract.json').read_bytes());assert all(ny(t)>0 for t in old['add_triangles_world_xyz_m']);c=copy.deepcopy(old);c['id']='NORTH_APPROACH_R04_CONTINUOUS_ROAD';c['add_triangles_world_xyz_m']=[[t[0],t[2],t[1]]for t in old['add_triangles_world_xyz_m']];c.update(triangle_convention='godot_clockwise_front',representation_kind='continuous_road_top',derived_from_rejected_winding=ref(BASE/'collision_contract.json'),correction='The Godot ConcavePolygonShape3D loader consumes collision contracts verbatim, unlike terrain surfaces. Reversed only b/c for all74 triangles; no native geometry or world profile changed.')
 assert all(ny(t)<0 for t in c['add_triangles_world_xyz_m']);assert all(sorted(map(tuple,a))==sorted(map(tuple,b))for a,b in zip(old['add_triangles_world_xyz_m'],c['add_triangles_world_xyz_m']))
 p=HERE/'collision_contract.json';assert not p.exists();p.write_text(json.dumps(c,separators=(',',':'))+'\n')
 binding_path=CITY/'registered_integration/r8/north_water_binding_r01.json';b=json.loads(binding_path.read_bytes());matches=[i for i,r in enumerate(b['collision_contracts'])if r['path']==str((BASE/'collision_contract.json').relative_to(ROOT))];assert len(matches)==1;b['collision_contracts'][matches[0]]=ref(p);b['evidence'].append(ref(HERE/'derive.py'));q=CITY/'registered_integration/r8/north_water_binding_r02.json';assert not q.exists();q.write_text(json.dumps(b,indent=2)+'\n');print(json.dumps(dict(contract=ref(p),binding=ref(q))))
if __name__=='__main__':run()
