"""Synthetic exact-output regressions only, with strict resource and wall limits."""
from __future__ import annotations
import copy,hashlib,importlib.util,itertools,json,math,pathlib,random,resource,signal,sys,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[4];sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
def timeout(*args):raise TimeoutError('30 second regression budget')
signal.signal(signal.SIGALRM,timeout);signal.alarm(30)
from voxel_character.common import core
from voxel_character.common import exact_sampling_v2
from types import SimpleNamespace
candidate=SimpleNamespace(compile_master=exact_sampling_v2.compile_master_v2, BudgetExceeded=core.BudgetExceeded)

def determinant(b):return b[0][0]*(b[1][1]*b[2][2]-b[1][2]*b[2][1])-b[0][1]*(b[1][0]*b[2][2]-b[1][2]*b[2][0])+b[0][2]*(b[1][0]*b[2][1]-b[1][1]*b[2][0])
rotations=[]
for perm in itertools.permutations(range(3)):
 for signs in itertools.product((-1,1),repeat=3):
  b=[[signs[i] if j==perm[i] else 0 for j in range(3)] for i in range(3)]
  if determinant(b)==1:rotations.append(b)

def build(pitch,rotation,offset,variant):
 e=pitch*core.EPS;center=pitch*.5
 if variant==0:a,b=center+e,center+2*pitch+e
 elif variant==1:a,b=math.nextafter(center+e,-math.inf),math.nextafter(center+2*pitch+e,math.inf)
 elif variant==2:a,b=math.nextafter(center+e,math.inf),math.nextafter(center+2*pitch+e,-math.inf)
 else:a,b=-2.5*pitch,1.5*pitch
 box={'kind':'box','min':[a,-2.5*pitch,-2.5*pitch],'max':[b,2.5*pitch,2.5*pitch],'minimum_cells':[0,0,0]}
 polygon=[[-2.5*pitch,-2.5*pitch],[2.5*pitch,-1.5*pitch],[1.5*pitch,2.5*pitch],[-2.5*pitch,2.5*pitch]]
 extrusion={'kind':'extrusion','polygon':polygon,'z_min':a,'z_max':b}
 ops=[{'id':'base','action':'paint','part':'solid','material':'a','shape':box},
      {'id':'overpaint','action':'paint','part':'solid','material':'b','shape':extrusion},
      {'id':'selected_cut','action':'cut','part':'solid','shape':{'kind':'box','min':[-pitch]*3,'max':[pitch]*3,'minimum_cells':[1,1,1],'anchors':['min','center','max']},'selector':{'material':'b'}}]
 return {'schema':core.SCHEMA,'id':'synthetic-boundary','revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[pitch*.1,-pitch*.2,pitch*.3],
         'materials':{'a':{},'b':{}},'components':[{'id':'body','parts':[{'id':'solid','pivot':[0,0,0]}],'operations':ops}],
         'instances':[{'id':'one','component':'body','transform':{'basis':rotation,'translation':offset}}, {'id':'two','component':'body','transform':{'basis':rotation,'translation':[x+pitch for x in offset]}}],
         'assembly_cuts':[{'id':'target_one','shape':{'kind':'box','min':[-pitch*4,-pitch*4,-pitch*4],'max':[0,pitch*4,pitch*4]},'selector':{'instance':'one'}}],
         'constraints':[{'id':'anything','kind':'nonempty'},{'id':'contact','kind':'touch','a':{'instance':'one'},'b':{'instance':'two'}},{'id':'connected','kind':'connected'}]}

def compare(m,pitch,bounds):
 kw={'cell_bounds':bounds,'max_candidate_cells':30000,'max_output_cells':2000}
 a=core.compile_master(m,{'pitch':pitch},**kw);b=candidate.compile_master(m,{'pitch':pitch},**kw)
 differences=[k for k,v in a.items() if k!='compiler_source_hash' and v!=b.get(k)]
 assert not differences,differences
 return len(a['cells']),a['candidate_cells']
start=time.perf_counter();cases=0;occupied=candidates=0
for p in (.05,.1):
 for rotation in rotations:
  for variant in range(4):
   offset=[-p*1.3,p*.7,-p*.9];m=build(p,rotation,offset,variant)
   n,c=compare(m,p,{'min':[-5,-5,-5],'max':[6,6,6]});cases+=1;occupied+=n;candidates+=c
# Arbitrary rotation, near-permutation matrix, other shape kinds and empty bounds use fallback.
for angle in (.123,1e-12):
 b=[[math.cos(angle),0,math.sin(angle)],[0,1,0],[-math.sin(angle),0,math.cos(angle)]]
 for kind,shape in [('annulus',{'kind':'annulus','inner_radius':.025,'outer_radius':.12,'y_min':-.1,'y_max':.1}),('lathe',{'kind':'lathe','profile':[[0,-.1],[.12,-.1],[.08,.1],[0,.1]]}),('tube',{'kind':'tube','points':[[-.1,0,0],[.1,.1,.1]],'radius':.04})]:
  m=build(.05,b,[0,0,0],0);m['components'][0]['operations'][0]['shape']=shape
  for bounds in ({'min':[-5]*3,'max':[6]*3},{'min':[0,0,0],'max':[0,1,1]}):
   n,c=compare(m,.05,bounds);cases+=1;occupied+=n;candidates+=c
# Existing candidate/output budget refusal must remain refusal.
budget_tests=[]
for budget in ({'max_candidate_cells':1,'max_output_cells':2000},{'max_candidate_cells':30000,'max_output_cells':1}):
 states=[]
 for module in (core,candidate):
  try:module.compile_master(build(.05,core.IDENTITY,[0,0,0],3),{'pitch':.05},**budget);states.append('passed')
  except core.BudgetExceeded:states.append('BudgetExceeded')
  except candidate.BudgetExceeded:states.append('BudgetExceeded')
 assert states==['BudgetExceeded']*2,states
 budget_tests.append(states)
report={'synthetic_cases_passed':cases,'proper_exact_signed_permutations':len(rotations),'pitches':[.05,.1],'aggregate_compared_occupied_cells':occupied,'aggregate_candidates_per_implementation':candidates,'candidate_output_budget_exceptions_match':budget_tests,'full_result_equality_excluding_compiler_source_hash':True,'coverage':['half-open epsilon boundaries','nextafter each side of boundaries','negative and fractional origins/translations','paint overwrite','instance-local selected cuts','assembly target cuts','duplicate shared component instances','nonempty/touch/connected constraints','arbitrary and near-axis rotation fallback','annulus/lathe/tube fallback','zero-width bounded ranges'],'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
(HERE/'regressions.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));signal.alarm(0)
