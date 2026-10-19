"""Isolated <=30 second, <=512 MiB benchmark. Never writes production paths."""
from __future__ import annotations
import cProfile, copy, hashlib, importlib.util, io, itertools, json, math, os, pathlib, pstats, resource, signal, sys, time
AUDIT=pathlib.Path(__file__).resolve().parent
ROOT=AUDIT.parents[4]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT.parent/'house_rules'))
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
def timeout(*args):raise TimeoutError('30 second audit budget')
signal.signal(signal.SIGALRM,timeout);signal.alarm(30)
from voxel_character.common import core
import layered_compile as layer

def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
source=pathlib.Path(core.__file__).read_text()
old='''        for point in itertools.product(*ranges):
            world = [o+(n+.5)*pitch for n, o in zip(point, origin)]
            if contains(shape, inverse(placement, world), epsilon=pitch*EPS):
                yield point
'''
hoist='''        inverse_basis = transpose(placement["basis"])
        delta_axes = [[(o+(n+.5)*pitch)-t for n in r]
                      for r,o,t in zip(ranges,origin,placement["translation"])]
        for offsets in itertools.product(*(range(len(r)) for r in ranges)):
            local = mv(inverse_basis, [delta_axes[j][offsets[j]] for j in range(3)])
            if contains(shape, local, epsilon=pitch*EPS):
                yield tuple(ranges[j][offsets[j]] for j in range(3))
'''
fast='''        inverse_basis = transpose(placement["basis"])
        exact_permutation = all(sum(v != 0 for v in row) == 1 and
                                all(v in (0,1,-1) for v in row)
                                for row in inverse_basis)
        if exact_permutation and shape["kind"] in ("box", "extrusion") and all(ranges):
            axis_map = [next(j for j,v in enumerate(row) if v != 0) for row in inverse_basis]
            baseline = [o+(r.start+.5)*pitch for o,r in zip(origin,ranges)]
            values = []
            for local_axis,world_axis in enumerate(axis_map):
                axis_values = {}
                for n in ranges[world_axis]:
                    world = list(baseline)
                    world[world_axis] = origin[world_axis]+(n+.5)*pitch
                    delta = [a-b for a,b in zip(world,placement["translation"])]
                    axis_values[n] = dot(inverse_basis[local_axis],delta)
                values.append(axis_values)
            epsilon = pitch*EPS
            if shape["kind"] == "box":
                accepted = [None,None,None]
                for j,world_axis in enumerate(axis_map):
                    accepted[world_axis] = [n for n,value in values[j].items()
                        if shape["min"][j]-epsilon <= value < shape["max"][j]-epsilon]
                yield from itertools.product(*accepted)
                return
            accepted_z = [n for n,value in values[2].items()
                          if shape["z_min"]-epsilon <= value < shape["z_max"]-epsilon]
            if not accepted_z:return
            point = [0,0,0]
            for nx,x in values[0].items():
                point[axis_map[0]] = nx
                for ny,y in values[1].items():
                    if not inside_polygon(x,y,shape["polygon"]):continue
                    point[axis_map[1]] = ny
                    for nz in accepted_z:
                        point[axis_map[2]] = nz
                        yield tuple(point)
            return
'''+old
assert source.count(old)==1
mods={}
for name,replacement in [('hoisted',hoist),('separable',fast)]:
 p=AUDIT/(name+'_core.py');p.write_text(source.replace(old,replacement));spec=importlib.util.spec_from_file_location('audit_'+name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);mods[name]=m
key='ordinary_r2_8c6ac6d806c93b'
catalog=json.loads((AUDIT.parent/'house_extensions/generated/active_catalog.json').read_text())
record=next(r for r in catalog['assets'] if r['asset_key']==key)
assert not any(p.name.startswith(key+'.layered.') for root in (AUDIT.parent/'house_rules/compiled',) for p in root.rglob('*')),'Do not resample an asset with existing outputs'
master=layer.load_master(ROOT/record['emitted_master_path'])
fine=layer.SpatialSource(master,.05,range_only=True)
# One 1.5m cube through an unsampled roof slope; geometry is never cropped.
bounds={'min':[-15,235,25],'max':[15,265,55]};origin=master.get('grid_origin',[0,0,0]);pitch=.05
lo=[origin[j]+bounds['min'][j]*pitch for j in range(3)]
hi=[origin[j]+bounds['max'][j]*pitch for j in range(3)]
bounded=fine.bounded_master(lo,hi)
selection={'asset_key':key,'source_path':record['emitted_master_path'],'source_sha256':record['emitted_master_sha256'],'bounds':bounds,'pitch':pitch,'retained_operations':sum(len(c['operations']) for c in bounded['components'])}
(AUDIT/'selection.json').write_text(json.dumps(selection,indent=2)+'\n')
(AUDIT/'bounded_master.json').write_text(json.dumps(bounded,separators=(',',':'))+'\n')
kwargs={'cell_bounds':bounds,'max_candidate_cells':300000,'max_output_cells':100000}
results={};timings={}
for name,module in [('reference',core),*mods.items()]:
 t=time.perf_counter();results[name]=module.compile_master(bounded,{'pitch':pitch},**kwargs);timings[name]=time.perf_counter()-t
prof=cProfile.Profile();prof.enable();profiled=core.compile_master(bounded,{'pitch':pitch},**kwargs);prof.disable()
prof.dump_stats(str(AUDIT/'reference.prof'))
s=io.StringIO();pstats.Stats(prof,stream=s).strip_dirs().sort_stats('cumulative').print_stats(35)
(AUDIT/'profile.txt').write_text(s.getvalue())
def row_hash(rows):return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def signatures(result):
 rows=result['cells'];points={tuple(r[:3]) for r in rows};faces=[]
 for r in rows:
  p=r[:3]
  for axis in range(3):
   for sign in (-1,1):
    q=list(p);q[axis]+=sign
    if tuple(q) not in points:faces.append([axis,sign,*p,r[5]])
 return {'occupied':len(rows),'faces':len(faces),'rows_hash':row_hash(rows),'occupied_hash':row_hash(sorted(points)),'material_hash':row_hash([r[:3]+[r[5]] for r in rows]),'exterior_face_hash':row_hash(sorted(faces))}
signatures_all={name:signatures(result) for name,result in results.items()}
reference=results['reference'];eq={}
for name,r in results.items():
 eq[name]={k:(v==r.get(k)) for k,v in reference.items() if k!='compiler_source_hash'}
 assert all(eq[name].values()),(name,[k for k,v in eq[name].items() if not v])
 assert signatures_all[name]==signatures_all['reference']
report={'schema':'riverstone.performance_audit.v1','selection':selection,'source_hashes':{'reference_core':sha(core.__file__),'layer_engine':sha(layer.__file__),**{n:sha(m.__file__) for n,m in mods.items()}},'wall_seconds':timings,'speedups':{n:timings['reference']/t for n,t in timings.items()},'candidate_cells':reference['candidate_cells'],'signatures':signatures_all,'full_result_equality_excluding_compiler_source_hash':{n:all(v.values()) for n,v in eq.items()},'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'profile_total_seconds':pstats.Stats(prof).total_tt,'shape_kinds':{k:sum(o['shape']['kind']==k for c in bounded['components'] for o in c['operations']) for k in ('box','extrusion')},'runtime_changes_applied':False,'note':'Timings are unprofiled and use identical inputs. cProfile is a separate baseline pass over this same bounded benchmark only. No compiled city cache was written.'}
(AUDIT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));print(s.getvalue())
signal.alarm(0)
