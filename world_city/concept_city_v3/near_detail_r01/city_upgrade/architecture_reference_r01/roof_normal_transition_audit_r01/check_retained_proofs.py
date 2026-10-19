#!/usr/bin/env python3
"""Independent range check on retained concrete examples; no geometry sampling."""
import sys,resource,gzip,json,math,time,hashlib
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(45,)*2)
O=Path(__file__).resolve().parent;A=O.parent
start=time.process_time();r=json.loads((O/'counts_and_proofs.json').read_text());ops={};links={}
for name in ('roof_repair_r02','roof_repair_r03'):
 with gzip.open(A/name/'roof_patch.master.json.gz','rt') as f:m=json.load(f)
 ops.update({o['id']:o for c in m['components'] for o in c['operations']})
 links.update({l['operation']:l for l in json.loads((A/name/'plan.json').read_text())['tile_source_links']})
checked=0;success=0;center_counterexamples=0
for why,groups in r['proof_examples'].items():
 for outcome,examples in groups.items():
  for p in examples:
   op=ops[p['source_tile_id']];B=op['transform']['basis'];t=op['transform']['translation'];top=op['shape']['polygon'][5:][::-1]
   def loc(v):return [sum(B[k][j]*(v[k]-t[k]) for k in range(3)) for j in range(3)]
   # Independent representation: concave polyline = minimum of its supporting affine facets.
   def height(x):return min(a[1]+(x-a[0])*(b[1]-a[1])/(b[0]-a[0]) for a,b in zip(top,top[1:]))
   for name,side in (('owner',-1),('exterior',1)):
    q=[]
    for v in p['unit_face_corners']:
     v=v.copy();v[p['axis']]+=side*p['sign']*.03125/2;q.append(loc(v))
    # local profile x uses only world Z, whereas local y uses only world X/Y;
    # their coordinate intervals on an axis-aligned face are independent.
    assert abs(B[0][0])+abs(B[1][0])+abs(B[2][1])<1e-12
    lo=min(v[0] for v in q);hi=max(v[0] for v in q)
    xs=[lo,hi]+[v[0] for v in top[1:-1] if lo<=v[0]<=hi]
    hs=[height(x) for x in xs]
    exact=[min(v[1] for v in q)-max(hs),max(v[1] for v in q)-min(hs)]
    key=name+'_plane_signed_top_range'
    if key in p:assert max(abs(a-b) for a,b in zip(exact,p[key]))<1e-9,(p,key,exact)
   if p.get('full_face_continuous_top_ownership_proven'):
    success+=1;assert min(p['full_prism_domain_margins'].values())>1e-9
    assert p['owner_plane_signed_top_range'][0]>=-.0625-1e-9 and p['owner_plane_signed_top_range'][1]<=1e-9
    assert p['exterior_plane_signed_top_range'][0]>1e-9
    assert p['axis']==1 and p['sign']==1
    assert min(p['touched_facet_cardinal_hemisphere'])>1e-10
   elif p['center_top_pair_proven']:center_counterexamples+=1
   checked+=1
out={'status':'PASS_RETAINED_EXAMPLES_ONLY','independent_formula':'Concave top = min of four supporting affine facet heights. On each axis-aligned dual face, local profile coordinate and local vertical coordinate are independent. Exact signed-height range is [min(local_y)-max(top), max(local_y)-min(top)], with top extrema at profile-range endpoints and enclosed authored knots. No sampling or original classifier/extrema helper used.', 'retained_examples_verified':checked,'positive_proof_examples':success,'center_only_false_positive_examples':center_counterexamples,'full_count_independently_replayed':False,'CPU_seconds':time.process_time()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
(O/'retained_proof_check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
