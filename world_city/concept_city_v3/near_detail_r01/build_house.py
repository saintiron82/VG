"""Bounded common compilation. Compressed occupancy is evidence, never runtime."""
from pathlib import Path
import argparse,gzip,json,resource,sys,time,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'voxel_character/common'))
from core import compile_master
from render_data import make_render_data

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--pitch',type=float,default=.05);ap.add_argument('--name',default='house_near');ap.add_argument('--master',default='house.master.json');args=ap.parse_args()
 out=HERE/'generated';out.mkdir(exist_ok=True)
 paths=[out/(args.name+s) for s in ['.cells.json.gz','.render.json','.stats.json']]
 if any(p.exists() for p in paths):raise SystemExit('Existing outputs preserved')
 master=json.loads((HERE/'source'/args.master).read_text());t=time.perf_counter()
 c=compile_master(master,{'pitch':args.pitch},max_candidate_cells=40000000,max_output_cells=3000000)
 elapsed=time.perf_counter()-t
 if not c['valid']:raise SystemExit(json.dumps(c['constraints']))
 print(json.dumps({'phase':'compiled','cells':len(c['cells']),'seconds':elapsed}),flush=True)
 with gzip.open(paths[0],'wt',encoding='utf-8',compresslevel=5) as f:json.dump(c,f,separators=(',',':'))
 t=time.perf_counter();r=make_render_data(c);paths[1].write_text(json.dumps(r,separators=(',',':'))+'\n')
 stats={'status':'PASS','pitch':args.pitch,'cells':len(c['cells']),'candidate_cells':c['candidate_cells'],'quads':r['quad_count'],'triangles':r['quad_count']*2,'compile_seconds':elapsed,'mesh_and_write_seconds':time.perf_counter()-t,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'master_hash':c['master_hash'],'payload_hash':c['payload_hash'],'bounds':r['bounds'],'constraints':c['constraints'],'files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths[:2]},'runtime_vertex_normal_bytes_nonindexed':r['quad_count']*6*24,'measurement_scope':'Cloud offline build. RSS process peak including compiler and greedy mesher, not GPU memory or Windows FPS.'}
 paths[2].write_text(json.dumps(stats,indent=2)+'\n');print(json.dumps(stats),flush=True)
if __name__=='__main__':main()
