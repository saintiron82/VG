import sys,json,hashlib,time,resource
from pathlib import Path
H=Path(__file__).resolve().parents[1];A=H.parent
sys.path.insert(0,str(A/'roof_repair_r04/validation_r01'))
from validate_render import stream_render,ref,save

def groups(path):
 out={}
 for g in stream_render(path)['groups']:
  m=g['material'];q=g['quads'][0]
  if m not in out:out[m]=[0,hashlib.sha256()]
  out[m][0]+=1;out[m][1].update(json.dumps(q,separators=(',',':')).encode()+b'\n')
 return {m:{'quads':n,'ordered_quad_geometry_sha256':h.hexdigest()}for m,(n,h)in out.items()}
t=time.monotonic();old=A/'roof_repair_r04/roof_repaired.render.json.gz';new=H/'roof_repaired.render.json.gz';a=groups(old);b=groups(new);result={m:{'original':a.get(m),'candidate':b.get(m),'ordered_geometry_equal':a.get(m)==b.get(m),'source_roof_palette':m.startswith('top_tile_')}for m in a.keys()|b.keys()};save(H/'validation_r02/render_group_identity.json',{'schema':'riverstone.roof_r05.render_group_identity.v1','original':ref(old),'candidate':ref(new),'groups':result,'all_nonroof_ordered_geometry_equal':all(r['ordered_geometry_equal']for r in result.values()if not r['source_roof_palette']),'caveat':'Material groups are not semantic parts. Foreground gable cells also use the six TOP palette colors. Source ownership and exterior unit-face proof are separate.','seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss});print(json.dumps({m:r['ordered_geometry_equal']for m,r in result.items()}))
