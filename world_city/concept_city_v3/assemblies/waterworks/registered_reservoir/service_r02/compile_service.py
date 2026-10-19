import collections,json,resource,time
from author_service import HERE,ROOT,ref,write
from voxel_character.common import coordinate_planes,render_data,core
if __name__=='__main__':
 t=time.monotonic();pre=json.loads((HERE/'preflight.json').read_text());s=json.loads((ROOT/pre['source']['path']).read_text());c=coordinate_planes.compile_master(s,{'pitch':.2},max_candidate_cells=600000,max_output_cells=200000);assert c['valid'];r=render_data.make_render_data(c);p=HERE/'cache'/f"{s['id']}.pitch_0.2.render.json";write(p,r);cells={tuple(row[:3]) for row in c['cells']};seen={next(iter(cells))};queue=collections.deque(seen)
 while queue:
  x,y,z=queue.popleft()
  for q in [(x-1,y,z),(x+1,y,z),(x,y-1,z),(x,y+1,z),(x,y,z-1),(x,y,z+1)]:
   if q in cells and q not in seen:seen.add(q);queue.append(q)
 report={'source':pre['source'],'cache':ref(p),'master_hash':core.digest(s),'pitch_m':.2,'candidate_cells':c['candidate_cells'],'output_cells':len(cells),'quad_count':r['quad_count'],'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'disconnected_cells':len(cells-seen),'status':'pass' if len(cells)==len(seen) else 'failed_connectivity'};write(HERE/'compile_report.json',report);print(json.dumps(report,indent=2));assert len(cells)==len(seen)
