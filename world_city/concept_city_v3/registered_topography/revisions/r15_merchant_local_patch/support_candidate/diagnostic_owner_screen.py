import sys,json,math,collections,time
sys.dont_write_bytecode=True
from world_city.concept_city_v3.registered_topography.revisions.r15_merchant_local_patch import author as a
s=json.loads((a.HERE/'source_contract.json').read_text());hist=collections.Counter();out=[];t=time.monotonic()
for i,r in enumerate(s['support_requirements']):
 p=r['polygon_xz_m']; xs,zs=zip(*p);ds=a.base.R04.prior._replacement_domains(p,[min(xs),min(zs),max(xs),max(zs)],a.EXCLUDED)
 for d in ds:
  hist[d['kind']]+=1
  q=d['polygon_xz_m'];cen=[sum(v[k] for v in q)/len(q) for k in(0,1)];eff=a.effective_record_after_retirement(*cen)
  if eff['owner_id']!=d['owner_id'] or abs(a.effective_source_height(*cen)-a.base.source_surface_height_at(d,*cen))>1e-8:out.append([r['id'],d['kind'],d['owner_id'],eff['kind'],eff['owner_id']])
print(json.dumps(dict(hist=hist,mismatches=out,elapsed=time.monotonic()-t),indent=2))
