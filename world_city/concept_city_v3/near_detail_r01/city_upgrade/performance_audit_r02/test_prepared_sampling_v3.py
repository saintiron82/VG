"""Independent old-core/v2/v3 equality and invariance; no production writes."""
from __future__ import annotations
import copy, dataclasses, hashlib, itertools, json, math, pathlib, resource, signal, sys, time
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT)); sys.dont_write_bytecode=True
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2)); signal.alarm(120)
from voxel_character.common import core, exact_sampling_v2 as v2, prepared_sampling_v3 as v3
ORIGINAL=core.compile_master
HASHES={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [pathlib.Path(core.__file__),pathlib.Path(v2.__file__)]}

def base(p=.05,basis=None,variant=3):
 e=p*core.EPS;center=.5*p
 limits=[(center+e,center+2*p+e),(math.nextafter(center+e,-math.inf),math.nextafter(center+2*p+e,math.inf)),(math.nextafter(center+e,math.inf),math.nextafter(center+2*p+e,-math.inf)),(-2.5*p,1.5*p)]
 a,b=limits[variant]
 ops=[{'id':'base','action':'paint','part':'solid','material':'a','shape':{'kind':'box','min':[a,-2.5*p,-2.5*p],'max':[b,2.5*p,2.5*p]}},
 {'id':'overpaint','action':'paint','part':'solid','material':'b','shape':{'kind':'extrusion','polygon':[[-2.5*p,-2.5*p],[2.5*p,-1.5*p],[1.5*p,2.5*p],[-2.5*p,2.5*p]],'z_min':a,'z_max':b}},
 {'id':'localcut','action':'cut','part':'solid','shape':{'kind':'box','min':[-p]*3,'max':[p]*3,'minimum_cells':[1,2,3],'anchors':['min','center','max']},'selector':{'material':['a','b'],'feature':['overpaint']}}]
 return {'schema':core.SCHEMA,'id':'prepared-equality','revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[p*.1,-p*.2,p*.3],
 'materials':{'a':{'rgb':[1,2,3]},'b':{'rgb':[4,5,6]}},'components':[{'id':'body','parts':[{'id':'solid','pivot':[0,0,0]}],'operations':ops}],
 'instances':[{'id':'one','component':'body','transform':{'basis':basis or core.IDENTITY,'translation':[-p*1.3,p*.7,-p*.9]}},{'id':'two','component':'body','parent':'one','transform':{'translation':[p,0,p]}}],
 'assembly_cuts':[{'id':'target','shape':{'kind':'box','min':[-p*4]*3,'max':[0,p*4,p*4]},'selector':{'instance':['one'],'component':'body'}}],
 'constraints':[{'id':'nonempty','kind':'nonempty'},{'id':'touch','kind':'touch','a':{'instance':'one'},'b':{'instance':'two'}},{'id':'connected','kind':'connected','selector':{'material':['b']}},{'id':'empty','kind':'empty_region','shape':{'kind':'box','min':[p*7]*3,'max':[p*8]*3}}],
 'extensions':{'ordered_notes':['source',{'keep':True}], 'tuple_metadata':('a',1)}}

def clean(result):
 return {k:v for k,v in result.items() if k not in ('compiler_source_hash','compiler_provenance')}

stats={'cases':0,'cells':0,'candidates':0,'budget_tests':0,'malformed_tests':0}
def compare(m,request,bounds=None,plan=None):
 kw={'cell_bounds':bounds,'max_candidate_cells':50000,'max_output_cells':10000}
 old=core.compile_master(m,request,**kw); fast=v2.compile_master_v2(m,request,**kw)
 prepared=plan or v3.prepare_master(m,request)
 new=v3.compile_prepared(prepared,**kw)
 assert clean(old)==clean(fast)==clean(new),[k for k in old if k!='compiler_source_hash' and old[k]!=new.get(k)]
 assert new['compiler_provenance']['plan_key']==prepared.plan_key
 assert new['master_hash']==prepared.source_hash==core.digest(m)
 assert v3.assert_plan_matches(prepared,m,request,source_hash=old['master_hash'],plan_key=prepared.plan_key)
 stats['cases']+=1;stats['cells']+=len(old['cells']);stats['candidates']+=old['candidate_cells']
 return old,new

def det(b):return b[0][0]*(b[1][1]*b[2][2]-b[1][2]*b[2][1])-b[0][1]*(b[1][0]*b[2][2]-b[1][2]*b[2][0])+b[0][2]*(b[1][0]*b[2][1]-b[1][1]*b[2][0])
rotations=[]
for perm in itertools.permutations(range(3)):
 for signs in itertools.product((-1,1),repeat=3):
  b=[[signs[i] if j==perm[i] else 0 for j in range(3)] for i in range(3)]
  if det(b)==1:rotations.append(b)

start=time.perf_counter()
for p in (.05,.1):
 for b in rotations:
  for variant in range(4):compare(base(p,b,variant),{'pitch':p},{'min':[-5]*3,'max':[6]*3})
for angle in (.123,1e-12):
 b=[[math.cos(angle),0,math.sin(angle)],[0,1,0],[-math.sin(angle),0,math.cos(angle)]]
 shapes=[{'kind':'box','min':[-.1]*3,'max':[.1]*3}, {'kind':'extrusion','polygon':[[-.1,-.1],[.1,-.1],[.1,.1],[-.1,.1]],'z_min':-.01,'z_max':.01,'minimum_cells':2,'anchor':'max'}, {'kind':'annulus','inner_radius':.025,'outer_radius':.12,'y_min':-.01,'y_max':.01,'minimum_cells_y':3}, {'kind':'lathe','profile':[[0,-.1],[.12,-.1],[.08,.1],[0,.1]]}, {'kind':'tube','points':[[-.1,0,0],[.1,.1,.1]],'radius':.01,'minimum_radius_cells':.8}]
 for shape in shapes:
  m=base(basis=b);m['components'][0]['operations'][0]['shape']=shape;plan=v3.prepare_master(m,{'reference_span':.5,'cells':10})
  for bounds in (None,{'min':[-5]*3,'max':[6]*3},{'min':[0,0,0],'max':[0,1,1]}):compare(m,{'reference_span':.5,'cells':10},bounds,plan)

# Full output vs 3-axis halo/ownership partitions, including holes and materials.
poly=[[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2],[-.2,-.2],[-.1,-.1],[-.1,.1],[.1,.1],[.1,-.1],[-.1,-.1],[-.2,-.2]]
assert not core.inside_polygon(0,0,poly)
def faces(rows,occupancy):
 out=set()
 for r in rows:
  for axis in range(3):
   for sign in (-1,1):
    q=r[:3];q[axis]+=sign
    if tuple(q) not in occupancy:out.add((axis,sign,*r[:3],r[5]))
 return out
seams=[]
for p in (.05,.1):
 for b in [core.IDENTITY,[[0,0,1],[0,1,0],[-1,0,0]]]:
  m=base(p,b);m['grid_origin']=[0,0,0];m['instances']=m['instances'][:1];m['instances'][0]['transform']={'basis':b};m['assembly_cuts']=[];m['constraints']=[]
  m['components'][0]['operations']=[{'id':'hole','action':'paint','part':'solid','material':'a','shape':{'kind':'extrusion','polygon':poly,'z_min':-.15,'z_max':.15}},{'id':'cut','action':'cut','part':'solid','shape':{'kind':'box','min':[-.05,-.3,-.3],'max':[.05,.3,.3]}},{'id':'refill','action':'paint','part':'solid','material':'b','shape':{'kind':'box','min':[-.025,-.25,-.025],'max':[.025,.25,.025]}}]
  plan=v3.prepare_master(m,{'pitch':p});full,_=compare(m,{'pitch':p},plan=plan);rows=[];exterior=set()
  for low in itertools.product((-8,0),repeat=3):
   high=[v+8 for v in low];bounds={'min':[v-1 for v in low],'max':[v+1 for v in high]};_,part=compare(m,{'pitch':p},bounds,plan)
   owned=[r for r in part['cells'] if all(low[j]<=r[j]<high[j] for j in range(3))];rows.extend(owned);exterior|=faces(owned,{tuple(r[:3]) for r in part['cells']})
  assert sorted(rows)==full['cells'];assert exterior==faces(full['cells'],{tuple(r[:3]) for r in full['cells']})
  seams.append({'pitch':p,'cells':len(rows),'external_faces':len(exterior),'materials':sorted(set(r[5] for r in rows))})

# Exact refusal type and message, including cumulative instance retention and
# candidate visits caused solely by semantic empty-region constraints.
def outcome(fn,*args,**kw):
 try:fn(*args,**kw);return ('success','')
 except Exception as e:return(type(e).__name__,str(e))
m=base();request={'pitch':.05}
for kw in ({'max_candidate_cells':1},{'max_output_cells':1},{'max_output_cells':50},{'max_candidate_cells':500},{'max_candidate_cells':False},{'max_output_cells':0}):
 states=[outcome(f,m,request,**kw) for f in (core.compile_master,v2.compile_master_v2,v3.compile_master_v3)]
 assert states[0]==states[1]==states[2] and states[0][0]!='success',states;stats['budget_tests']+=1
one=base();one['instances']=one['instances'][:1];one['components'][0]['operations']=[{'id':'only','action':'paint','part':'solid','material':'a','shape':{'kind':'box','min':[0,0,0],'max':[.05,.05,.05]}}];one['instances'][0]['transform']={};one['grid_origin']=[0,0,0];one['assembly_cuts']=[];one['constraints']=[{'id':'region','kind':'empty_region','shape':{'kind':'box','min':[1,1,1],'max':[1.1,1.1,1.1]}}]
for budget in (1,8):
 states=[outcome(f,one,request,max_candidate_cells=budget) for f in (core.compile_master,v2.compile_master_v2,v3.compile_master_v3)];assert states[0]==states[1]==states[2] and states[0][0]=='BudgetExceeded',states;stats['budget_tests']+=1

malformed=[]
for field,value in [('schema','wrong'),('revision',0),('grid_origin',[0,0,float('nan')]),('materials',{}),('instances',[]),('components',[])]:
 x=base();x[field]=value;malformed.append((x,request,{}))
for field,value in [('action','erase'),('material','unknown'),('part','unknown'),('selector',{'unknown':'x'}),('shape',{'kind':'box','min':[0]*3,'max':[0]*3}),('transform',{'basis':[[2,0,0],[0,1,0],[0,0,1]]})]:
 x=base();x['components'][0]['operations'][0][field]=value;malformed.append((x,request,{}))
for request_bad in ({'pitch':0},{'pitch':.05,'cells':10},{'cells':True,'reference_span':1},{'pitch':float('inf')},None):malformed.append((base(),request_bad,{}))
for bounds in ({'min':[0]*3},{'min':[0]*3,'max':[1,1,False]},{'min':[1]*3,'max':[0]*3}):malformed.append((base(),request,{'cell_bounds':bounds}))
x=base();x['instances'][0]['parent']='two';malformed.append((x,request,{}))
x=base();x['instances'][1]['parent']='missing';malformed.append((x,request,{}))
x=base();x['components'].append(copy.deepcopy(x['components'][0]));malformed.append((x,request,{}))
x=base();x['constraints'][0]['minimum_cells']=0;malformed.append((x,request,{}))
for x,r,kw in malformed:
 states=[outcome(f,x,r,**kw) for f in (core.compile_master,v2.compile_master_v2,v3.compile_master_v3)]
 assert states[0]==states[1]==states[2] and states[0][0]!='success',states;stats['malformed_tests']+=1

# Caller mutations, output mutations and nested plan mutations cannot affect a
# prepared source. Changed source and backend identities require explicit keys.
m=base();r={'pitch':.05,'label':['first']};pristine=copy.deepcopy(m);plan=v3.prepare_master(m,r);before=v3.compile_prepared(plan);oldkey=plan.plan_key
m['revision']=2;m['components'][0]['operations'][0]['shape']['max'][0]+=.2;m['materials']['a']['rgb'][0]=99;m['extensions']['ordered_notes'][1]['keep']=False;r['label'][0]='second'
assert v3.compile_prepared(plan)==before
changed=v3.prepare_master(m,r);assert changed.plan_key!=oldkey and changed.source_hash!=plan.source_hash
assert v3.compile_prepared(changed)['payload_hash']!=before['payload_hash']
for kwargs in ({'master':m},{'request':r},{'source_hash':'0'*64},{'plan_key':'v2-checkpoint'}):assert outcome(v3.assert_plan_matches,plan,**kwargs)[0]=='PlanSourceMismatch'
assert hashlib.sha256(plan.source_snapshot_json).hexdigest()==core.digest(pristine)
assert outcome(setattr,plan,'source_hash','broken')[0]=='FrozenInstanceError'
try:plan._layers[0][0].sample.shape['min']=(99,99,99);raise AssertionError('mutable shape mapping')
except TypeError:pass
try:plan._layers[0][0].sample.shape['min'][0]=99;raise AssertionError('mutable nested shape')
except TypeError:pass
before['materials']['a']['rgb'][0]=123;before['cells'].clear();before['instances'][0]['world_transform']['basis'][0][0]=123
assert clean(v3.compile_prepared(plan))==clean(core.compile_master(pristine,{'pitch':.05,'label':['first']}))
assert outcome(v3.prepare_master,pristine,request,max_plan_bytes=1)[0]=='BudgetExceeded'
# Same-pitch request changes still change identity; semantic equality is not a
# license to resume a different explicit request/source.
same_request=v3.prepare_master(pristine,{'pitch':.05,'label':['different']})
assert same_request.source_hash==plan.source_hash and same_request.plan_key!=plan.plan_key
revision_only=copy.deepcopy(pristine);revision_only['revision']+=1
assert v3.prepare_master(revision_only,{'pitch':.05,'label':['first']}).plan_key!=plan.plan_key
# An overlapping second instance must still count toward retained output budget
# before any assembly cut can discard it.
retained=copy.deepcopy(one);retained['constraints']=[];retained['instances'].append({'id':'duplicate','component':'body'})
states=[outcome(f,retained,request,max_output_cells=1) for f in (core.compile_master,v2.compile_master_v2,v3.compile_master_v3)]
assert states==[('BudgetExceeded','retained/output-cell budget exceeded')]*3,states;stats['budget_tests']+=1
# Check the reviewed-file guard without ever modifying either reviewed file.
expected=v3.REFERENCE_CORE_SHA256
try:
 v3.REFERENCE_CORE_SHA256='0'*64
 assert outcome(v3.get_sampler_provenance)[0]=='ReferenceCompilerMismatch'
finally:v3.REFERENCE_CORE_SHA256=expected
# Explicit provenance tampering in a fresh immutable copy must be rejected.
bad=dataclasses.replace(plan,provenance=type(plan.provenance)({**plan.provenance,'sampler_version':'other'}))
assert outcome(v3.compile_prepared,bad)[0]=='PlanSourceMismatch'
assert outcome(v3.assert_plan_matches,dataclasses.replace(plan,source_snapshot_json=b'{}'))[0]=='PlanSourceMismatch'
assert core.compile_master is ORIGINAL
assert HASHES=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [pathlib.Path(core.__file__),pathlib.Path(v2.__file__)]}
report={'schema':'riverstone.prepared_sampling.regression.v1','passed':True,**stats,'proper_axis_rotations':len(rotations),'seam_checks':seams,'full_result_equality':'all fields except explicitly different compiler_source_hash/compiler_provenance','caller_and_output_mutation_isolation':True,'nested_plan_immutable':True,'explicit_source_request_checkpoint_guards':True,'plan_memory_budget_refusal':True,'original_core_and_v2_unchanged':HASHES,'provenance':v3.get_sampler_provenance(),'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
(HERE/'regressions.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));signal.alarm(0)
