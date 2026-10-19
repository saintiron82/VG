"""Bound road query IO by exact selected-triangle AABBs, never nominal tile bounds."""
from pathlib import Path
import hashlib,json,struct
H=Path(__file__).resolve().parent;R=H.parents[3];C=H.parents[1]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=H/'road_surfaces/generated/source_index.json';d=read(p);i=read(C/'playable_r01/generated/tile_r01/index.json');bounds={}
for key,row in d['tiles'].items():
 if not row['eligible_face_count']:continue
 path=R/i['tiles'][key]['terrain_path'];data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==row['source_binary_sha256']
 lo=[float('inf')]*3;hi=[-float('inf')]*3
 for a,b,_ in row['eligible_face_runs']:
  for n in range(a,b):
   for v in range(3):
    q=struct.unpack_from('<3d',data,n*88+v*24)
    lo=[min(x,y) for x,y in zip(lo,q)];hi=[max(x,y) for x,y in zip(hi,q)]
 bounds[key]={'min':lo,'max':hi}
out={'schema':'riverstone.city.road_detail_catalog.v1','policy_path':str(p.relative_to(R)),'policy_sha256':sha(p),'source_city_index_sha256':d['source_tile_index']['sha256'],'eligible_source_bounds':bounds,'radius_m':10,'max_modules':120,'max_faces':4096,'update_seconds':.5,'observer_refresh_distance_m':1.25,'binary_cache_budget_bytes':12*1024*1024,'no_collision_change':True,'whole_city_upgrade_complete':False}
p=C/'playable_detail_r01/road_catalog.json';p.write_text(json.dumps(out,indent=2)+'\n');print(p,len(bounds),p.stat().st_size)
