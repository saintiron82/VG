"""Check finite TOP regions survive the final source-priority union."""
from pathlib import Path
import gzip,hashlib,json,os,resource,time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(15,)*2)
h=Path(__file__).resolve().parent;t=time.monotonic()
a=np.load(h/'upper_union_arrays.npz');m=a['materials'];lo=a['origin_cell_xyz'];ret=a['retained_baseline']
c=json.loads(gzip.decompress((h/'roof_patch.compiled.json.gz').read_bytes()));visible={};blocked={}
for x,y,z,instance,part,material,feature in c['cells']:
 if part!='measured_tile_regions':continue
 iy,ix,iz=y-lo[1],x-lo[0],z-lo[2];visible.setdefault(feature,0);blocked.setdefault(feature,0)
 if ret[iy,ix,iz]:blocked[feature]+=1
 elif iy+1>=m.shape[0] or m[iy+1,ix,iz]<0:visible[feature]+=1
assert len(visible)==339 and all(n>0 for n in visible.values())
r={'status':'PASS_ALL_FINITE_REGIONS_HAVE_FINAL_POSITIVE_Y_EXTERIOR','region_count':len(visible),'regions_with_visible_top_faces':sum(n>0 for n in visible.values()),'regions_with_source_priority_blocking':sum(n>0 for n in blocked.values()),'tile_cells_blocked_by_unchanged_source':sum(blocked.values()),'visible_positive_y_unit_faces_by_region':visible,'candidate_render_sha256':hashlib.sha256((h/'roof_repaired.render.json.gz').read_bytes()).hexdigest(),'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
p=h/'visible_regions.json';assert not p.exists();p.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='visible_positive_y_unit_faces_by_region'}))
