"""Actual cache column support and measured surface clearance, no guessed hull."""
import json,math
from .author import HERE,ROOT,read,old
from world_city.runtime_city.checks import placement as g

def cols(d):
 out={};p=d['pitch']
 for c in d['cells']:
  k=c[0],c[2];b,t=c[1]*p,(c[1]+1)*p
  if k in out:out[k]=[min(out[k][0],b),max(out[k][1],t)]
  else:out[k]=[b,t]
 return out

def run():
 p=read(HERE/'profile.json');pack=read(HERE/'resolved_placements.json');assets=pack['assets'];compiled=[read(ROOT/r['compiled']['path'])for r in assets];cc=[cols(c)for c in compiled];fg=compiled[2]['pitch'];checks=[];fail=[]
 profiles=[dict(poly=[[v[0],v[2]]for v in r['triangle_local_xyz_m']],plane=old.plane(r['triangle_local_xyz_m']))for r in p['triangles']]
 ix=g._SpatialIndex(4)
 for i,r in enumerate(profiles):ix.add(i,r['poly'])
 maxgap=-999;errlo=999;errhi=-999;coarse_protrusion=-999;outside=0
 for (x,z),(bottom,top)in cc[2].items():
  q=[(x+.5)*fg,(z+.5)*fg];hits=[r for i in ix.candidates([q])if g.point_in_convex_polygon(q,(r:=profiles[i])['poly'],1e-8)]
  if not hits:outside+=1;continue
  hs=[r['plane'][0]*q[0]+r['plane'][1]*q[1]+r['plane'][2]for r in hits];h=sum(hs)/len(hs);assert max(hs)-min(hs)<1e-6
  e=top-h;errlo=min(errlo,e);errhi=max(errhi,e)
  supports=[]
  for a,d in zip(cc[:2],compiled[:2]):
   pitch=d['pitch'];cell=a.get((math.floor(q[0]/pitch),math.floor(q[1]/pitch)))
   if cell:supports.append(cell[1])
  if not supports:fail.append(dict(xz=q,kind='no_native_support'));continue
  st=max(supports);gap=bottom-st;maxgap=max(gap,maxgap);coarse_protrusion=max(coarse_protrusion,st-h)
  if gap>1e-8:fail.append(dict(xz=q,kind='vertical_support_gap',gap_m=gap,cover_bottom_m=bottom,support_top_m=st))
 result=dict(status='PASS'if not fail and errlo>=-.08 and errhi<=.08 and coarse_protrusion<=0 else'FAIL',samples=len(cc[2])-outside,actual_native_columns=len(cc[2]),optional_apron_samples=outside,maximum_support_gap_m=maxgap,minimum_visible_top_error_m=errlo,maximum_visible_top_error_m=errhi,maximum_support_protrusion_above_profile_m=coarse_protrusion,failures=fail[:50],total_failures=len(fail),limits=['Column-center diagnostic; full polygon/cell coverage and gate sweep still required.'])
 (HERE/'native_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='failures'},indent=2));assert result['status']=='PASS'
if __name__=='__main__':run()
