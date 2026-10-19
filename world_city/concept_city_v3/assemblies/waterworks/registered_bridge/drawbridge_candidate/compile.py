"""Five bounded native caches, with unchanged common compiler and mesher."""
import json,time,resource
from voxel_character.common import coordinate_planes,render_data,core
from .author import HERE,ROOT,load,write,ref

def compile_all():
 pre=load(HERE/'compile_preflight.json');reports=[]
 for item in pre['assets']:
  started=time.monotonic();m=load(ROOT/item['master']['path']);assert ref(ROOT/item['master']['path'])==item['master'];pitch=item['pitch_m']
  c=coordinate_planes.compile_master(m,{'pitch':pitch},max_candidate_cells=4_000_000,max_output_cells=900_000)
  assert c['candidate_cells']==item['candidate_cells'],(c['candidate_cells'],item['candidate_cells'])
  path=HERE/'cache'/f'{item["asset_key"]}.pitch_{pitch}.compiled.json';write(path,c)
  report={**item,'compiled':ref(path),'valid':c['valid'],'constraints':c['constraints'],'cell_count':len(c['cells']),'compile_seconds':time.monotonic()-started,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
  if c['valid']:
   r=render_data.make_render_data(c);path=HERE/'cache'/f'{item["asset_key"]}.pitch_{pitch}.render.json';write(path,r);report.update(render=ref(path),quad_count=r['quad_count'],bounds=r['bounds'],total_seconds=time.monotonic()-started)
  reports.append(report);write(HERE/'compile_report.json',{'candidate':ref(HERE/'candidate.json'),'reports':reports,'all_valid':all(q['valid'] for q in reports),'total_seconds':sum(q.get('total_seconds',q['compile_seconds']) for q in reports),'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024});print(json.dumps({k:report.get(k) for k in ('asset_key','valid','cell_count','quad_count','total_seconds','peak_rss_mib')}),flush=True)
  if not c['valid']:raise RuntimeError('Native source constraints failed: '+item['asset_key'])
if __name__=='__main__':compile_all()
