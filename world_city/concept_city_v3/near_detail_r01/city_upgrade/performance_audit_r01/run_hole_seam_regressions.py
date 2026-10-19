import copy,hashlib,importlib.util,itertools,json,math,pathlib,resource,signal,sys,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[4];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));signal.alarm(30)
from voxel_character.common import core
from voxel_character.common import exact_sampling_v2
from types import SimpleNamespace
candidate=SimpleNamespace(compile_master=exact_sampling_v2.compile_master_v2, BudgetExceeded=core.BudgetExceeded)
poly=[[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2],[-.2,-.2],[-.1,-.1],[-.1,.1],[.1,.1],[.1,-.1],[-.1,-.1],[-.2,-.2]]
assert not core.inside_polygon(0,0,poly) and core.inside_polygon(.15,0,poly)
rotations=[[[1,0,0],[0,1,0],[0,0,1]],[[0,0,1],[0,1,0],[-1,0,0]],[[-1,0,0],[0,1,0],[0,0,-1]],[[0,0,-1],[0,1,0],[1,0,0]]]
base={'schema':core.SCHEMA,'id':'hole-seam','revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'materials':{'stone':{},'paint':{}},'components':[{'id':'c','parts':[{'id':'solid','pivot':[0,0,0]}],'operations':[{'id':'hole','action':'paint','part':'solid','material':'stone','shape':{'kind':'extrusion','polygon':poly,'z_min':-.15,'z_max':.15}},{'id':'cut','action':'cut','part':'solid','shape':{'kind':'box','min':[-.05,-.3,-.3],'max':[.05,.3,.3]}},{'id':'refill','action':'paint','part':'solid','material':'paint','shape':{'kind':'box','min':[-.025,-.25,-.025],'max':[.025,.25,.025]}}]}],'instances':[{'id':'i','component':'c'}]}
def faces(rows,occupied,owned=None):
 out=[]
 for r in rows:
  p=r[:3]
  if owned is not None and not all(owned[0][j]<=p[j]<owned[1][j] for j in range(3)):continue
  for axis in range(3):
   for sign in (-1,1):
    q=list(p);q[axis]+=sign
    if tuple(q) not in occupied:out.append((axis,sign,*p,r[5]))
 return set(out)
checks=[]
for pitch in (.05,.1):
 for rotation in rotations:
  m=copy.deepcopy(base);m['instances'][0]['transform']={'basis':rotation,'translation':[0,0,0]};a=core.compile_master(m,{'pitch':pitch});b=candidate.compile_master(m,{'pitch':pitch});assert all(v==b[k] for k,v in a.items() if k!='compiler_source_hash')
  rows=[];exposed=set()
  for low in itertools.product((-8,0),repeat=3):
   high=[v+8 for v in low];bounds={'min':[v-2 for v in low],'max':[v+2 for v in high]}
   ca=core.compile_master(m,{'pitch':pitch},cell_bounds=bounds);cb=candidate.compile_master(m,{'pitch':pitch},cell_bounds=bounds);assert all(v==cb[k] for k,v in ca.items() if k!='compiler_source_hash')
   own=[r for r in cb['cells'] if all(low[j]<=r[j]<high[j] for j in range(3))];rows.extend(own);exposed|=faces(own,{tuple(r[:3]) for r in cb['cells']})
  assert sorted(rows)==a['cells'];fa=faces(a['cells'],{tuple(r[:3]) for r in a['cells']});assert exposed==fa
  checks.append({'pitch':pitch,'basis':rotation,'cells':len(rows),'faces':len(fa),'rows_hash':a['payload_hash'],'exterior_face_hash':hashlib.sha256(json.dumps(sorted(fa),separators=(',',':')).encode()).hexdigest()})
report={'cases':len(checks),'bounded_chunk_comparisons':len(checks)*8,'all_full_results_exact_except_compiler_source_hash':True,'all_halo_owned_partitions_match_full_cells':True,'all_halo_owned_exterior_faces_match_full':True,'geometry':['bridged polygon representing a hole with original even-odd predicate','cut followed by repaint','0/90/180/270 degree exact rotation','three-axis chunk seams and corners','unbounded full compile compared to bounded halo union'],'checks':checks,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
(HERE/'hole_seam_regressions.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
