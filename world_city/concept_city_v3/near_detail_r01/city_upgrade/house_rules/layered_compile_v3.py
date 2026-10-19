"""Bounded common compilation with conservative lossless interior aggregation.

This explicit v3 session prepares two immutable original full-source plans once.
Only candidate ranges change per chunk; sampling predicates and global aggregation remain exact.
The reference common/core.py and original engine remain immutable. Optional integer bounds
restrict candidate ranges without changing predicates, operation order or cuts.
Both .05/.1 are compiled by the same backwards-compatible common compiler.
A core cell is admitted only when its eight fine cells and semantic labels agree,
and it has no exposed fine face. Exposed geometry always remains .05m.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import copy
import fcntl
import gzip
import hashlib
import itertools
import io
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time

HERE=Path(__file__).resolve().parent
if (__name__=='__main__' and (HERE/'.queue_handoff').exists() and
        os.environ.get('RIVERSTONE_QUEUE_HANDOFF_SHA256')!=hashlib.sha256((HERE/'.queue_handoff').read_bytes()).hexdigest()):
    print(json.dumps({'status':'PENDING_QUEUE_CONTROLLER_HANDOFF','asset_key':sys.argv[1],
        'before_common_import':True,'cell_sampling_started':False}),flush=True)
    raise SystemExit(77)
if __name__=='__main__' and (HERE/'.compile_pause').exists():
    print('Compilation paused before common import for approved compiler migration',flush=True)
    while (HERE/'.compile_pause').exists():time.sleep(1)
    os.execv(sys.executable,[sys.executable,*sys.argv])
sys.path.insert(0,str(HERE))
import adapter as a
import connected_constraints
import polygon_crop_guard
import render_only_retention
import chunk_enumeration
import checkpoint_store
import output_reservations_v3
from voxel_character.common import exact_sampling_v2, prepared_sampling_v3

EXPECTED_SAMPLER_SHA256="fc1d25b73b3158394c6559246288ded2f5b882c80389b12695a254100239dfd7"
EXPECTED_RESERVATION_SHA256="4585bb869ec736e30e524ec6d408db9ed3adceda7d82b336225b8f0079bd9b55"

def verified_sampler_provenance():
    provenance=prepared_sampling_v3.get_sampler_provenance()
    a.fail(a.sha(output_reservations_v3.__file__)==EXPECTED_RESERVATION_SHA256,"v3_reservation_source_not_reviewed")
    a.fail(provenance["implementation_sha256"]==EXPECTED_SAMPLER_SHA256,"v3_sampler_source_not_reviewed")
    a.fail(provenance["reference_core_sha256"]==a.sha(a.core.__file__),"v3_reference_core_mismatch")
    return provenance
from voxel_character.common.render_data import make_render_data


class Fingerprint:
    def __init__(self):self.count=0;self.xor=0;self.sum=0
    def add(self,row):
        value=int.from_bytes(hashlib.blake2b(json.dumps(row,separators=(',',':'),ensure_ascii=False).encode(),digest_size=32).digest(),'big')
        self.count+=1;self.xor^=value;self.sum=(self.sum+value)%(1<<256)
    def merge(self,other):
        self.count+=other.count;self.xor^=other.xor;self.sum=(self.sum+other.sum)%(1<<256)
    def value(self):return {'count':self.count,'xor256':f'{self.xor:064x}','sum256':f'{self.sum:064x}'}


def signed_permutation(basis):
    return all(sum(abs(v)>1e-8 for v in row)==1 and all(abs(v-round(v))<1e-8 for v in row) for row in basis)


def clip_polygon(poly,axis,bound,greater):
    result=[]
    for i,p in enumerate(poly):
        q=poly[i-1]
        pin=p[axis]>=bound if greater else p[axis]<=bound
        qin=q[axis]>=bound if greater else q[axis]<=bound
        if pin!=qin:
            ratio=(bound-q[axis])/(p[axis]-q[axis])
            result.append([q[j]+ratio*(p[j]-q[j]) for j in range(2)])
        if pin:result.append(p)
    return result


def crop_prepared_shape(shape,world_transform,world_lo,world_hi,sample_grid=None,guard_stats=None):
    points=[a.core.inverse(world_transform,p) for p in itertools.product(*zip(world_lo,world_hi))]
    lo=[min(p[i] for p in points) for i in range(3)]
    hi=[max(p[i] for p in points) for i in range(3)]
    shape=copy.deepcopy(shape)
    shape.pop('minimum_cells',None);shape.pop('anchors',None);shape.pop('anchor',None)
    if shape['kind']=='box':
        shape['min']=[max(x,y) for x,y in zip(shape['min'],lo)]
        shape['max']=[min(x,y) for x,y in zip(shape['max'],hi)]
        return shape if all(x<y-1e-10 for x,y in zip(shape['min'],shape['max'])) else None
    if shape['kind']=='extrusion':
        shape['z_min']=max(shape['z_min'],lo[2]);shape['z_max']=min(shape['z_max'],hi[2])
        if shape['z_min']>=shape['z_max']-1e-10:return None
        original_polygon=copy.deepcopy(shape['polygon']);poly=shape['polygon']
        for axis in (0,1):
            poly=clip_polygon(poly,axis,lo[axis],True)
            poly=clip_polygon(poly,axis,hi[axis],False)
        clean=[]
        for p in poly:
            if not clean or any(abs(x-y)>1e-10 for x,y in zip(clean[-1],p)):clean.append(p)
        if len(clean)>1 and all(abs(x-y)<1e-10 for x,y in zip(clean[0],clean[-1])):clean.pop()
        area=sum(clean[i][0]*clean[i-1][1]-clean[i-1][0]*clean[i][1] for i in range(len(clean))) if len(clean)>=3 else 0
        if len(clean)<3 or abs(area)<1e-12:clean=[]
        if sample_grid is not None:
            check=polygon_crop_guard.check_polygon_samples(a.core,original_polygon,clean,world_transform,world_lo,world_hi,sample_grid['origin'],sample_grid['pitch'])
            if guard_stats is not None:
                guard_stats['operations_checked']+=1;guard_stats['grid_samples_checked']+=check['sample_count']
            if not check['pass']:
                clean=original_polygon
                if guard_stats is not None:
                    guard_stats['original_polygons_retained']+=1
                    if len(guard_stats['examples'])<8:guard_stats['examples'].append(check)
        if not clean:return None
        shape['polygon']=clean
        return shape
    raise a.UnsupportedSurface('layer_shape_pending',{'kind':shape['kind']})


class SpatialSource:
    def __init__(self,master,pitch,range_only=False):
        self.master=master;self.pitch=pitch;self.range_only=range_only
        self.polygon_guard_stats={'operations_checked':0,'grid_samples_checked':0,'original_polygons_retained':0,'examples':[]}
        components,instances=a.core.validate_master(master,pitch)
        counts=Counter(i['component'] for i in instances.values())
        self.shared_components=any(n!=1 for n in counts.values())
        if not range_only:a.fail(not self.shared_components,'layer_shared_component_instances_pending',dict(counts))
        a.fail(all(c['kind'] in ('nonempty','connected') for c in master.get('constraints',[])),'layer_global_constraint_kind_pending')
        self.transforms={};visiting=set()
        def resolve(key):
            if key in self.transforms:return self.transforms[key]
            a.fail(key not in visiting,'layer_instance_cycle')
            visiting.add(key);i=instances[key];t=a.core.transform(i.get('transform'))
            if i.get('parent'):t=a.core.compose(resolve(i['parent']),t)
            self.transforms[key]=t;visiting.remove(key);return t
        self.items=[];paint_bounds=[];self.instance_bounds={}
        for instance in instances.values():
            t=resolve(instance['id']);component=components[instance['component']];ops=[]
            for operation in component['operations']:
                placement=a.core.compose(t,a.core.transform(operation.get('transform')))
                if not range_only:a.fail(signed_permutation(placement['basis']),'layer_non_axis_aligned_transform_pending',{'instance':instance['id'],'operation':operation['id']})
                shape=a.core.prepare_shape(operation['shape'],pitch)
                if not range_only:a.fail(shape['kind'] in ('box','extrusion'),'layer_shape_pending',{'kind':shape['kind']})
                lo,hi=a.core.shape_bounds(shape)
                corners=[a.core.apply(placement,p) for p in itertools.product(*zip(lo,hi))]
                low=[min(p[i] for p in corners) for i in range(3)];high=[max(p[i] for p in corners) for i in range(3)]
                ops.append((operation,shape,placement,low,high))
                if operation['action']=='paint':paint_bounds.append((low,high))
            self.instance_bounds[instance['id']]=([min(o[3][j] for o in ops) for j in range(3)],[max(o[4][j] for o in ops) for j in range(3)]) if ops else None
            self.items.append((instance,component,t,ops))
        self.cuts=[]
        for cut in master.get('assembly_cuts',[]):
            placement=a.core.transform(cut.get('transform'));shape=a.core.prepare_shape(cut['shape'],pitch)
            if not range_only:a.fail(signed_permutation(placement['basis']),'layer_assembly_cut_transform_pending')
            self.cuts.append((cut,shape,placement))
        self.bounds=([min(p[0][i] for p in paint_bounds) for i in range(3)],[max(p[1][i] for p in paint_bounds) for i in range(3)])

    def bounded_master(self,world_lo,world_hi):
        """Only prune disjoint ops; never alter original shape predicates.

        Shared component instances use a safe unpruned original-master fallback.
        Actual sample bounds are passed separately to the common compiler.
        """
        if self.shared_components:
            result=copy.deepcopy(self.master);result['constraints']=[]
            return result
        master={k:copy.deepcopy(v) for k,v in self.master.items() if k not in ('components','instances','constraints','metadata','provenance')}
        master.update(components=[],instances=[],constraints=[])
        for instance,component,t,ops in self.items:
            span=self.instance_bounds[instance['id']]
            if span is None or any(span[1][j]<=world_lo[j] or span[0][j]>=world_hi[j] for j in range(3)):continue
            retained=[copy.deepcopy(original) for original,shape,placement,lo,hi in ops
                      if not any(hi[j]<=world_lo[j] or lo[j]>=world_hi[j] for j in range(3))]
            if not retained:continue
            c={k:copy.deepcopy(v) for k,v in component.items() if k!='operations'};c['operations']=retained
            i=copy.deepcopy(instance);i.pop('parent',None);i['transform']=t
            master['components'].append(c);master['instances'].append(i)
        if not master['components']:
            instance,component,t,_=self.items[0]
            c={k:copy.deepcopy(v) for k,v in component.items() if k!='operations'};c['operations']=[]
            i=copy.deepcopy(instance);i.pop('parent',None);i['transform']=t
            master['components']=[c];master['instances']=[i]
        return master

    def crop(self,world_lo,world_hi):
        master={k:copy.deepcopy(v) for k,v in self.master.items() if k not in ('components','instances','constraints','assembly_cuts','metadata','provenance')}
        master.update(components=[],instances=[],constraints=[],assembly_cuts=[])
        for instance,component,t,ops in self.items:
            output=[]
            for original,shape,placement,lo,hi in ops:
                if any(hi[j]<=world_lo[j] or lo[j]>=world_hi[j] for j in range(3)):continue
                clipped=crop_prepared_shape(shape,placement,world_lo,world_hi,{'origin':self.master.get('grid_origin',[0,0,0]),'pitch':self.pitch},self.polygon_guard_stats)
                if clipped:
                    op=copy.deepcopy(original);op['shape']=clipped;output.append(op)
            if not output:continue
            c={k:copy.deepcopy(v) for k,v in component.items() if k!='operations'};c['operations']=output
            i=copy.deepcopy(instance);i.pop('parent',None);i['transform']=t
            master['components'].append(c);master['instances'].append(i)
        if not master['components']:
            instance,component,t,_=self.items[0]
            c={k:copy.deepcopy(v) for k,v in component.items() if k!='operations'};c['operations']=[]
            i=copy.deepcopy(instance);i.pop('parent',None);i['transform']=t
            master['components']=[c];master['instances']=[i]
        for original,shape,placement in self.cuts:
            clipped=crop_prepared_shape(shape,placement,world_lo,world_hi,{'origin':self.master.get('grid_origin',[0,0,0]),'pitch':self.pitch},self.polygon_guard_stats)
            if clipped:
                op=copy.deepcopy(original);op['shape']=clipped;master['assembly_cuts'].append(op)
        return master


def owned(point,lo,hi):return all(lo[j]<=point[j]<hi[j] for j in range(3))


def expected_faces(rows,all_cells):
    result=set()
    for row in rows:
        p=tuple(row[:3])
        for axis in range(3):
            u,v=(axis+1)%3,(axis+2)%3
            for sign in (-1,1):
                q=list(p);q[axis]+=sign
                if tuple(q) not in all_cells:
                    result.add((axis,sign,p[axis]+(sign>0),p[u],p[v],row[5]))
    return result


def owned_quads(render,lo,hi,rules):
    origin,pitch=render['grid_origin'],render['pitch']
    output=[];faces=set();count=0
    for group in render['groups']:
        material=group['material']
        for q in group['quads']:
            grid=[[int(round((p[j]-origin[j])/pitch)) for j in range(3)] for p in q]
            a.fail(all(abs((q[k][j]-origin[j])/pitch-grid[k][j])<rules['vertex_grid_tolerance'] for k in range(4) for j in range(3)),'layer_vertex_off_grid')
            axes=[j for j in range(3) if len({p[j] for p in grid})==1]
            a.fail(len(axes)==1,'layer_nonplanar_quad')
            axis=axes[0];u,v=(axis+1)%3,(axis+2)%3;plane=grid[0][axis]
            aa=[grid[1][j]-grid[0][j] for j in range(3)];bb=[grid[2][j]-grid[0][j] for j in range(3)]
            normal=aa[u]*bb[v]-aa[v]*bb[u]
            a.fail(normal!=0,'layer_zero_area_quad')
            sign=1 if normal>0 else -1
            owner=plane-1 if sign>0 else plane
            if not lo[axis]<=owner<hi[axis]:continue
            u0,u1=max(lo[u],min(p[u] for p in grid)),min(hi[u],max(p[u] for p in grid))
            v0,v1=max(lo[v],min(p[v] for p in grid)),min(hi[v],max(p[v] for p in grid))
            if u1<=u0 or v1<=v0:continue
            corners=[]
            for uu,vv in ((u0,v0),(u1,v0),(u1,v1),(u0,v1)):
                p=[0,0,0];p[axis]=plane;p[u]=uu;p[v]=vv
                corners.append([round(origin[j]+p[j]*pitch,rules['vertex_decimal_places']) for j in range(3)])
            if sign<0:corners.reverse()
            output.append((material,corners))
            for uu in range(u0,u1):
                for vv in range(v0,v1):
                    face=(axis,sign,plane,uu,vv,material)
                    a.fail(face not in faces,'layer_duplicate_surface_face')
                    faces.add(face);count+=1
    return output,faces


def split_cells(fine,coarse,lo,hi,rules):
    cells={tuple(row[:3]):row for row in fine['cells']}
    own=[row for row in fine['cells'] if owned(row[:3],lo,hi)]
    selected={};protected=re.compile(rules['protected_feature_regex'])
    for row in coarse['cells']:
        base=[row[j]*2 for j in range(3)]
        if not owned(base,lo,hi):continue
        if row[4] in rules['protected_parts'] or protected.fullmatch(row[6]):continue
        children=[tuple(base[j]+delta[j] for j in range(3)) for delta in itertools.product((0,1),repeat=3)]
        if any(p not in cells or cells[p][3:]!=row[3:] for p in children):continue
        if any(q not in cells for p in children for q in a.core.neighbors(p)):continue
        selected[tuple(row[:3])]=row
    near=[row for row in own if tuple(row[j]//2 for j in range(3)) not in selected]
    a.fail(len(near)+8*len(selected)==len(own),'layer_cell_partition_count_mismatch')
    return own,near,list(selected.values()),cells


def load_master(path):
    path=Path(path)
    with (gzip.open(path,'rt',encoding='utf-8') if path.suffix=='.gz' else path.open(encoding='utf-8')) as stream:
        return json.load(stream)


def time_limit(signum,frame):
    raise TimeoutError('Per-asset wall time limit of 900 seconds exceeded')


def commit_progress(path,value):
    temporary=path.with_name(path.name+'.tmp')
    a.write(temporary,value);os.replace(temporary,path)


def run(asset_key,output_dir=None,rules_path=None,catalog_path=None,render_only=False,checkpoint_policy_path=None,resume_checkpoint=False):
    invocation_started=time.perf_counter()
    a.fail(render_only,'v3_reserved_rollout_requires_render_only')
    sampler_provenance=verified_sampler_provenance()
    rules_path=Path(rules_path or HERE/'layer_rules.v1.json').resolve();rules=a.load(rules_path)
    a.fail('shared_output_reservation' in rules,'v3_atomic_output_reservation_required')
    a.fail(rules['fine_pitch_m']==.05 and rules['core_pitch_m']==.1,'layer_grid_ratio_contract')
    edge=rules['chunk_edge_fine_cells'];halo=rules['halo_fine_cells']
    a.fail(type(edge)is int and edge>0 and edge%2==0 and halo>=2 and halo%2==0,'layer_chunk_grid_contract')
    output=Path(output_dir or HERE/'compiled').resolve();output.mkdir(parents=True,exist_ok=True)
    inherited_soft,inherited_hard=resource.getrlimit(resource.RLIMIT_AS)
    effective_memory_limit=rules['memory_limit_bytes'] if inherited_hard==resource.RLIM_INFINITY else min(rules['memory_limit_bytes'],inherited_hard)
    resource.setrlimit(resource.RLIMIT_AS,(effective_memory_limit,effective_memory_limit))
    catalog_path=Path(catalog_path or HERE/'generated/active_catalog.json').resolve();catalog=a.load(catalog_path)
    record=next((r for r in catalog['assets'] if r['asset_key']==asset_key),None)
    a.fail(record and record.get('emitted_master_path'),'layer_source_missing')
    master_path=a.ROOT/record['emitted_master_path'];source_path=a.ROOT/record['source_master_path']
    a.fail(a.sha(master_path)==record['emitted_master_sha256'],'layer_authored_master_hash_mismatch')
    a.fail(a.sha(source_path)==record['source_sha256'],'layer_original_source_hash_mismatch')
    master=load_master(master_path);fine_source=SpatialSource(master,.05,range_only=True)
    plan_started=time.perf_counter()
    max_plan_bytes=rules.get('max_prepared_plan_bytes_per_pitch',100663296)
    a.fail(type(max_plan_bytes)is int and 0<max_plan_bytes<=100663296,'v3_plan_memory_contract')
    fine_plan=prepared_sampling_v3.prepare_master(master,{'pitch':.05},max_plan_bytes=max_plan_bytes)
    coarse_plan=prepared_sampling_v3.prepare_master(master,{'pitch':.1},max_plan_bytes=max_plan_bytes)
    for plan,pitch in ((fine_plan,.05),(coarse_plan,.1)):
        prepared_sampling_v3.assert_plan_matches(plan,master,{'pitch':pitch})
    prepared_plan_seconds=time.perf_counter()-plan_started
    plan_identity={label:{'plan_key':plan.plan_key,'source_hash':plan.source_hash,'request_hash':plan.request_hash,
        'pitch':plan.pitch,'grid_origin':list(plan.grid_origin),'operation_count':plan.operation_count}
        for label,plan in (('fine',fine_plan),('core',coarse_plan))}
    plan_metrics={'prepare_seconds':prepared_plan_seconds,'fine_retained_bytes':fine_plan.retained_bytes,
        'core_retained_bytes':coarse_plan.retained_bytes,'total_retained_bytes':fine_plan.retained_bytes+coarse_plan.retained_bytes,
        'max_retained_bytes_per_pitch':max_plan_bytes,'original_constraints_preserved_in_plans':True,
        'bounded_constraint_results_used_as_global':False}
    origin=master.get('grid_origin',[0,0,0]);bounds=fine_source.bounds
    low=[math.floor((bounds[0][j]-origin[j])/.05+a.core.EPS) for j in range(3)]
    high=[math.ceil((bounds[1][j]-origin[j])/.05-a.core.EPS) for j in range(3)]
    starts=[range((low[j]//edge)*edge,high[j],edge) for j in range(3)]
    chunk_plan=chunk_enumeration.enumerate_paint_chunks(fine_source,origin,edge,a.core.EPS)
    owned_lows=chunk_plan.pop('owned_lows');chunk_count=len(owned_lows)
    policy_path=Path(checkpoint_policy_path or HERE/'checkpoint_policy.v1.json').resolve()
    policy=a.load(policy_path) if policy_path.exists() else {}
    checkpoint_enabled=render_only and asset_key in policy.get('enabled_asset_keys',[])
    a.fail(not resume_checkpoint or checkpoint_enabled,'checkpoint_resume_not_enabled')
    if checkpoint_enabled:
        a.fail(policy.get('max_sessions')==2 and policy.get('per_session_wall_seconds')==900 and
            0<policy.get('soft_stop_seconds',0)<=840,'checkpoint_policy_limit_contract')
    wall_limit=rules.get('wall_time_limit_seconds',900)
    a.fail(not checkpoint_enabled or wall_limit==900,'checkpoint_session_wall_limit_contract')
    a.fail(type(wall_limit)is int and 0<wall_limit<=1800,'layer_wall_time_limit_contract')
    paths={k:output/(asset_key+'.layered'+k+('.gz' if k=='.render.json' else '')) for k in ('.cells.jsonl.gz','.render.json','.stats.json')}
    partial={k:p.with_suffix(p.suffix+'.partial') for k,p in paths.items()}
    progress_path=output/(asset_key+'.layered.progress.json')
    protected=list(paths.values())+list(partial.values())+([] if resume_checkpoint else [progress_path,output/(asset_key+'.layered.blocked.json')])
    a.fail(not any(p.exists() for p in protected),'layer_existing_outputs_preserved')
    budget_root=HERE/'compiled'
    budget_roots=[budget_root,HERE.parent/'facility_roofs/compiled_priority_r01']
    if not any(output.is_relative_to(root.resolve()) for root in budget_roots):budget_roots.append(output)
    used=sum(p.stat().st_size for root in budget_roots for p in root.rglob('*') if p.is_file())
    used+=sum(p.stat().st_size for p in (HERE/'replay_code').rglob('*') if p.is_file())
    a.fail(used<rules['total_output_budget_bytes']-(2_000_000 if render_only else 15_000_000),'layer_output_budget_margin_insufficient')
    header={'kind':'header','schema':'riverstone.house_detail.layered_cells.v1','asset_key':asset_key,
            'source_id':master['id'],'source_revision':master['revision'],'master_hash':a.core.digest(master),
            'authored_master_sha256':record['emitted_master_sha256'],'source_master_sha256':record['source_sha256'],
            'fine_pitch_m':.05,'coarse_pitch_m':.1,'grid_origin':origin,'materials':master['materials'],
            'compiler_source_sha256':a.sha(a.core.__file__),'sampling_contract':'original_shapes_integer_cell_bounds_v1','chunk_edge_fine_cells':edge,'halo_fine_cells':halo,'layer_engine_sha256':a.sha(__file__),
            'layer_rules_sha256':a.sha(rules_path),'connectivity_source_sha256':a.sha(connected_constraints.__file__),'polygon_guard_source_sha256':a.sha(polygon_crop_guard.__file__),'authoring_seed':master.get('metadata',{}).get('city_near_material',{}).get('seed',master.get('provenance',{}).get('city_near_material_extension',{}).get('seed')),'input_catalog_sha256':a.sha(catalog_path),'source_constraints':master.get('constraints',[]),
            'core_policy':'Conservative complete same-label eight-cell aggregation; all exposed cells and protected detail remain fine.',
            'chunks':chunk_count,'cell_row_layout':['x','y','z','instance','part','material','feature']}
    header['sampling_backend']=sampler_provenance
    header['prepared_plans']=plan_identity
    active_file_keys=('.render.json',) if render_only else ('.cells.jsonl.gz','.render.json')
    header['storage_mode']='render_only_transient_cells' if render_only else 'retained_layered_cells'
    header['chunk_enumeration_sha256']=a.sha(chunk_enumeration.__file__)
    header['chunk_enumeration']=chunk_plan
    replay_paths={'core':a.core.__file__,'engine':__file__,'adapter':a.__file__,
        'exact_sampling_v2':exact_sampling_v2.__file__,'prepared_sampling_v3':prepared_sampling_v3.__file__,'output_reservations_v3':output_reservations_v3.__file__,
        'connected_constraints':connected_constraints.__file__,'polygon_crop_guard':polygon_crop_guard.__file__,
        'retention':render_only_retention.__file__,'chunk_enumeration':chunk_enumeration.__file__,
        'render_data':sys.modules[make_render_data.__module__].__file__,'mesh':sys.modules['mesh'].__file__,
        'rules':rules_path,'catalog':catalog_path,'checkpoint_store':checkpoint_store.__file__,
        **({'checkpoint_policy':policy_path} if policy_path.exists() else {})}
    header['replay_dependency_hashes']={key:a.sha(path) for key,path in replay_paths.items()}
    header['checkpoint_store_sha256']=a.sha(checkpoint_store.__file__)
    reservation_config=rules['shared_output_reservation']
    book=output_reservations_v3.ReservationBook(a.ROOT/reservation_config['book_path'],a.ROOT,
        [a.ROOT/p for p in reservation_config['retained_roots']],reservation_config['limit_bytes'],
        min_free_disk_bytes=reservation_config['min_free_disk_bytes'])
    reservation_key=asset_key+'@'+str(output.relative_to(a.ROOT))
    header['output_reservation']={'key':reservation_key,'book_path':reservation_config['book_path'],
        'cap_bytes':reservation_config['asset_cap_bytes'],'shared_limit_bytes':reservation_config['limit_bytes'],
        'release_requires_final_qa':True}
    reservation_identity={'header':header,'output_directory':str(output.relative_to(a.ROOT))}
    prior_reservation=book.record(reservation_key)
    if prior_reservation is not None:
        reservation_scopes=prior_reservation['scopes']
    else:
        reservation_scopes=[{'directory':str(output.relative_to(a.ROOT)),'prefix':asset_key+'.layered'}]
        for role,path in replay_paths.items():
            path=Path(path);snapshot=HERE/'replay_code'/(role+'_'+a.sha(path)[:16]+path.suffix)
            if not snapshot.exists():reservation_scopes.append({'directory':str(snapshot.parent.relative_to(a.ROOT)),'prefix':snapshot.name})
    book.reserve(reservation_key,reservation_scopes,reservation_config['asset_cap_bytes'],reservation_identity)
    def reserve_bytes(additional,emergency=False):
        book.check(reservation_key,additional+(0 if emergency else 65536))
        current=sum(p.stat().st_size for root in budget_roots for p in root.rglob('*') if p.is_file())
        current+=sum(p.stat().st_size for p in (HERE/'replay_code').rglob('*') if p.is_file())
        a.fail(current+additional+(0 if emergency else 65536)<=rules['total_output_budget_bytes'],
            'layer_prewrite_budget_exceeded',{'current':current,'additional_peak_bytes':additional,'limit':rules['total_output_budget_bytes']})
    def encoded_json(value):
        return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')
    def commit_checked(path,value,emergency=False):
        payload=encoded_json(value);reserve_bytes(len(payload),emergency)
        temporary=path.with_name(path.name+'.tmp')
        with temporary.open('wb') as stream:stream.write(payload);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        directory_fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(directory_fd)
        finally:os.close(directory_fd)
    class BudgetedWriter:
        def __init__(self,raw):self.raw=raw
        def write(self,data):reserve_bytes(len(data));return self.raw.write(data)
        def flush(self):return self.raw.flush()
        def tell(self):return self.raw.tell()
    if policy_path.exists():header['checkpoint_policy_sha256']=a.sha(policy_path)
    start=invocation_started;all_fp=Fingerprint();face_fp=Fingerprint();groups=defaultdict(list);chunk_stats=[]
    total_fine=total_core=candidate_total=0;mins=[math.inf]*3;maxs=[-math.inf]*3
    constraints=Counter();connected={c['id']:connected_constraints.ConnectedAccumulator() for c in master.get('constraints',[]) if c['kind']=='connected'};instance_to_component={i['id']:i['component'] for i in master['instances']}
    a.fail(time.perf_counter()-start<wall_limit,'v3_preparation_exceeded_session_wall_limit')
    lock=(HERE/'compile.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close();raise SystemExit('Another house compiler is active')
    try:book.acquire_writer(reservation_key)
    except Exception:
        fcntl.flock(lock,fcntl.LOCK_UN);lock.close();raise
    def stop_checkpoint():
        report={'schema':'riverstone.house_detail.resumable_checkpoint.v1','status':'PENDING_RESUMABLE_CHECKPOINT' if sessions_started<policy['max_sessions'] else 'PENDING_CHECKPOINT_SESSION_LIMIT','asset_key':asset_key,
            'completed_chunks':checkpoint.completed_count,'total_chunks':chunk_count,'session':sessions_started,
            'session_elapsed_seconds':time.perf_counter()-start,'max_sessions':policy['max_sessions'],
            'total_wall_budget_seconds':policy['max_sessions']*policy['per_session_wall_seconds'],
            'checkpoint_directory':str(checkpoint_path.relative_to(a.ROOT)),
            'checkpoint_manifest_sha256':a.sha(checkpoint.manifest_path),'source_and_recipe_unchanged':True,
            'resampling_completed_chunks_required':False,'retained_cell_payload':False}
        execution_ledger['sessions'][-1].update(status=report['status'],elapsed_seconds=time.perf_counter()-start,
            completed_chunks=checkpoint.completed_count)
        commit_checked(ledger_path,execution_ledger)
        commit_checked(output/(asset_key+'.layered.resumable.json'),report)
        progress.update(status=report['status'],session=sessions_started)
        commit_checked(progress_path,progress);print(json.dumps(report),flush=True);return report
    previous_alarm=signal.signal(signal.SIGALRM,time_limit);signal.alarm(max(1,wall_limit-math.ceil(time.perf_counter()-start)))
    checkpoint=None;resume_start=0;prior_elapsed=0.;sessions_started=1;execution_ledger=None;ledger_path=None;session_registered=False
    try:
        if checkpoint_enabled:
            checkpoint_path=output/(asset_key+'.layered.checkpoint')
            a.fail(checkpoint_path.exists()==resume_checkpoint,'checkpoint_explicit_resume_required')
            identity={'schema':'riverstone.house_detail.checkpoint_identity.v1','header':header,'owned_lows':[list(v) for v in owned_lows],
                'policy':policy,'helper_sha256':a.sha(checkpoint_store.__file__),
                'source_paths':{'master':str(master_path.relative_to(a.ROOT)),'source':str(source_path.relative_to(a.ROOT)),
                    'catalog':str(catalog_path.relative_to(a.ROOT)),'rules':str(rules_path.relative_to(a.ROOT))}}
            if not resume_checkpoint:reserve_bytes(len(encoded_json(identity))+16384)
            checkpoint=checkpoint_store.Store(checkpoint_path,identity)
            ledger_path=output/(asset_key+'.layered.checkpoint_sessions.json')
            execution_ledger=a.load(ledger_path) if ledger_path.exists() else {'identity_digest':checkpoint.identity_digest,'sessions':[]}
            a.fail(execution_ledger['identity_digest']==checkpoint.identity_digest,'checkpoint_session_identity_mismatch')
            a.fail(len(execution_ledger['sessions'])<policy['max_sessions'],'checkpoint_total_session_limit')
            a.fail(bool(execution_ledger['sessions'])==resume_checkpoint,'checkpoint_session_history_mismatch')
            sessions_started=len(execution_ledger['sessions'])+1
            execution_ledger['sessions'].append({'session':sessions_started,'started_epoch_seconds':time.time(),
                'wall_limit_seconds':wall_limit,'status':'RUNNING','resumed':resume_checkpoint})
            commit_checked(ledger_path,execution_ledger)
            session_registered=True
            if resume_checkpoint:
                saved=checkpoint.load_state();resume_start=checkpoint.completed_count
                a.fail(saved is not None and 0<resume_start<=chunk_count,'checkpoint_empty_or_invalid_resume')
                a.fail(saved['sessions_started']<sessions_started,'checkpoint_saved_session_mismatch')
                prior_elapsed=saved['elapsed_seconds']
                for number,saved_record in enumerate(checkpoint.load_records()):
                    summary=saved_record['chunk_stats']
                    a.fail(summary['chunk']==[v//edge for v in owned_lows[number]],'checkpoint_chunk_order_mismatch')
                    a.fail(summary['quads']==len(saved_record['quads']),'checkpoint_quad_count_mismatch')
                    chunk_stats.append(summary)
                    for material,quad in saved_record['quads']:groups[material].append(quad)
                for target,values in ((all_fp,saved['all_fingerprint']),(face_fp,saved['face_fingerprint'])):
                    target.count=values['count'];target.xor=int(values['xor256'],16);target.sum=int(values['sum256'],16)
                total_fine=saved['total_fine'];total_core=saved['total_core'];candidate_total=saved['candidate_total']
                mins=saved['mins'] if saved['mins'] is not None else [math.inf]*3
                maxs=saved['maxs'] if saved['maxs'] is not None else [-math.inf]*3
                constraints=Counter(saved['constraints'])
                a.fail(set(saved['connected'])==set(connected),'checkpoint_constraint_set_mismatch')
                connected={key:checkpoint_store.restore_connected(value) for key,value in saved['connected'].items()}
                replayed_occupancy=Fingerprint()
                for summary in chunk_stats:
                    values=summary['full_fine_fingerprint'];part=Fingerprint()
                    part.count=values['count'];part.xor=int(values['xor256'],16);part.sum=int(values['sum256'],16)
                    replayed_occupancy.merge(part)
                a.fail(all_fp.value()==replayed_occupancy.value(),'checkpoint_occupancy_certificate_aggregate_mismatch')
                a.fail(candidate_total==sum(r['near_candidate_cells']+r['core_candidate_cells'] for r in chunk_stats),'checkpoint_candidate_count_mismatch')
                a.fail(all_fp.count==sum(r['reference_owned_fine_cells'] for r in chunk_stats) and
                    face_fp.count==sum(r['visible_unit_faces'] for r in chunk_stats) and
                    total_fine==sum(r['stored_fine_cells'] for r in chunk_stats) and
                    total_core==sum(r['stored_core_cells'] for r in chunk_stats),'checkpoint_accumulated_count_mismatch')
                progress={'schema':'riverstone.house_detail.chunk_progress.v1','asset_key':asset_key,'status':'RESUMED',
                    'completed':resume_start,'chunks':chunk_count,'stored_fine':total_fine,'stored_core':total_core,
                    'fine_equivalent_cells':all_fp.count,'quads':sum(len(g) for g in groups.values()),'visible_unit_faces':face_fp.count,
                    'seconds':prior_elapsed,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        with render_only_retention.cell_stream(partial['.cells.jsonl.gz'],render_only) as stream:
            if stream is not None:stream.write(json.dumps(header,separators=(',',':'),ensure_ascii=False)+'\n')
            for number,lo in enumerate(owned_lows):
                if number<resume_start:continue
                if checkpoint_enabled and (time.perf_counter()-start>=policy['soft_stop_seconds'] or
                    (policy.get('fixture_stop_after_chunks') and number-resume_start>=policy['fixture_stop_after_chunks'])):
                    return stop_checkpoint()
                tick=time.perf_counter();lo=list(lo);hi=[x+edge for x in lo]
                clip_lo=[origin[j]+(lo[j]-halo)*.05 for j in range(3)]
                clip_hi=[origin[j]+(hi[j]+halo)*.05 for j in range(3)]
                fine_bounds={'min':[v-halo for v in lo],'max':[v+halo for v in hi]}
                coarse_bounds={k:[v//2 for v in values] for k,values in fine_bounds.items()}
                fine=prepared_sampling_v3.compile_prepared(fine_plan,cell_bounds=fine_bounds,max_candidate_cells=rules['max_chunk_candidate_cells'],max_output_cells=rules['max_chunk_output_cells'])
                coarse=prepared_sampling_v3.compile_prepared(coarse_plan,cell_bounds=coarse_bounds,max_candidate_cells=rules['max_chunk_candidate_cells'],max_output_cells=rules['max_chunk_output_cells'])
                for result,plan in ((fine,fine_plan),(coarse,coarse_plan)):
                    expected={**sampler_provenance,'plan_key':plan.plan_key,'source_hash':plan.source_hash,'request_hash':plan.request_hash}
                    a.fail(result['compiler_provenance']==expected,'v3_sampler_or_plan_provenance_changed')
                    a.fail(result.get('global_constraints_evaluated') is False,'v3_bounded_constraints_not_global')
                own,near,core,cells=split_cells(fine,coarse,lo,hi,rules)
                fp=Fingerprint();selected_connected={key:[] for key in connected}
                for row in own:
                    fp.add(row)
                    for j in range(3):mins[j]=min(mins[j],row[j]);maxs[j]=max(maxs[j],row[j]+1)
                    cell={'instance':row[3],'component':instance_to_component[row[3]],'part':row[4],'material':row[5],'feature':row[6]}
                    for constraint in master.get('constraints',[]):
                        if a.core.selector_matches(constraint.get('selector',{}),cell):
                            constraints[constraint['id']]+=1
                            if constraint['kind']=='connected':selected_connected[constraint['id']].append(tuple(row[:3]))
                for key,points in selected_connected.items():connected[key].add_chunk(points,lo,hi)
                all_fp.merge(fp)
                expected=expected_faces(own,cells)
                if fine['cells']:
                    quads,actual=owned_quads(make_render_data(fine),lo,hi,rules)
                else:quads,actual=[],set()
                a.fail(actual==expected,'layer_surface_ownership_or_seam_mismatch',{'chunk':number,'missing':len(expected-actual),'extra':len(actual-expected)})
                for face in actual:face_fp.add(list(face))
                for material,quad in quads:groups[material].append(quad)
                row={'kind':'chunk','chunk':[x//edge for x in lo],'owned_bounds_fine':[lo,hi],
                     'fine_cells':near,'coarse_cells':core,'full_fine_fingerprint':fp.value()}
                if stream is not None:stream.write(json.dumps(row,separators=(',',':'),ensure_ascii=False)+'\n')
                expanded_proof=None
                if render_only:
                    expanded_proof=Fingerprint()
                    for item in near:expanded_proof.add(item)
                    for item in core:
                        for delta in itertools.product((0,1),repeat=3):expanded_proof.add([*(2*item[j]+delta[j] for j in range(3)),*item[3:]])
                    a.fail(expanded_proof.value()==fp.value(),'transient_full_fine_reconstruction_mismatch')
                total_fine+=len(near);total_core+=len(core);candidate_total+=fine['candidate_cells']+coarse['candidate_cells']
                chunk_stats.append({'chunk':row['chunk'],'owned_bounds_fine':[lo,hi],'reference_owned_fine_cells':len(own),'stored_fine_cells':len(near),'stored_core_cells':len(core),
                    'near_candidate_cells':fine['candidate_cells'],'core_candidate_cells':coarse['candidate_cells'],
                    'visible_unit_faces':len(actual),'quads':len(quads),'seconds':time.perf_counter()-tick,'seam_and_overlap_check':True,**({'full_fine_fingerprint':fp.value(),'expanded_fingerprint':expanded_proof.value()} if render_only else {})})
                progress={'schema':'riverstone.house_detail.chunk_progress.v1','status':'RUNNING','phase':'layer_chunk','asset_key':asset_key,
                    'completed':number+1,'chunks':chunk_count,'dense_bbox_chunks':chunk_plan['dense_bbox_chunks'],
                    'proven_empty_chunks_skipped':chunk_plan['proven_empty_chunks_skipped'],'current_chunk':row['chunk'],
                    'current_chunk_quads':len(quads),'current_chunk_fingerprint':fp.value(),'stored_fine':total_fine,'stored_core':total_core,
                    'fine_equivalent_cells':all_fp.count,'quads':sum(len(g) for g in groups.values()),'visible_unit_faces':face_fp.count,
                    'seconds':time.perf_counter()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    'memory_limit_bytes':effective_memory_limit,'wall_time_limit_seconds':wall_limit,
                    'authored_master_sha256':header['authored_master_sha256'],'compiler_source_sha256':header['compiler_source_sha256'],'layer_engine_sha256':header['layer_engine_sha256']}
                if checkpoint_enabled:
                    saved={'all_fingerprint':all_fp.value(),'face_fingerprint':face_fp.value(),'total_fine':total_fine,'total_core':total_core,
                        'candidate_total':candidate_total,'mins':mins if all_fp.count else None,'maxs':maxs if all_fp.count else None,
                        'constraints':dict(constraints),'connected':{key:checkpoint_store.serialize_connected(value) for key,value in connected.items()},
                        'sessions_started':sessions_started,'elapsed_seconds':prior_elapsed+time.perf_counter()-start}
                    checkpoint.append(number,{'chunk_stats':chunk_stats[-1],'quads':[[material,quad] for material,quad in quads]},saved,
                        budget_check=reserve_bytes)
                    progress.update(checkpoint_committed_chunks=checkpoint.completed_count,checkpoint_manifest_sha256=a.sha(checkpoint.manifest_path),session=sessions_started)
                commit_checked(progress_path,progress)
                if number%10==0 or number+1==chunk_count:print(json.dumps(progress),flush=True)
                del fine,coarse,own,near,core,cells,expected,actual,quads,row
        if checkpoint_enabled and time.perf_counter()-start>=policy['soft_stop_seconds']:return stop_checkpoint()
        a.fail(all_fp.count>0,'layer_no_visible_occupancy')
        checks=[]
        for c in master.get('constraints',[]):
            if c['kind']=='connected':checks.append({'id':c['id'],'kind':c['kind'],**connected[c['id']].result()})
            else:checks.append({'id':c['id'],'kind':'nonempty','pass':constraints[c['id']]>=c.get('minimum_cells',1),'occupied_fine_reference_cells':constraints[c['id']]})
        a.fail(all(c['pass'] for c in checks),'layer_global_constraints_failed',{'checks':checks})
        a.fail(sampler_provenance==verified_sampler_provenance(),'v2_sampler_changed_during_run')
        a.fail(header['layer_engine_sha256']==a.sha(__file__),'layer_engine_changed_during_run')
        a.fail(header['compiler_source_sha256']==a.sha(a.core.__file__),'common_source_changed_during_run')
        a.fail(header['replay_dependency_hashes']=={key:a.sha(path) for key,path in replay_paths.items()},'replay_dependency_changed_during_run')
        a.fail(a.sha(master_path)==header['authored_master_sha256'],'authored_master_changed_during_run')
        a.fail(a.sha(source_path)==header['source_master_sha256'],'original_source_changed_during_run')
        gzip_sha=a.core.digest({'master_hash':header['master_hash'],'grid_origin':origin,'fine_occupancy_fingerprint':all_fp.value()}) if render_only else a.sha(partial['.cells.jsonl.gz'])
        render={'schema':'riverstone.voxel.render.v1','unit':'m','source_id':master['id'],'source_revision':master['revision'],
            'master_hash':a.core.digest(master),'payload_hash':gzip_sha,'pitch':.05,'grid_origin':origin,'materials':master['materials'],
            'cell_count':all_fp.count,'bounds':{'min':[round(origin[j]+mins[j]*.05,8) for j in range(3)],'max':[round(origin[j]+maxs[j]*.05,8) for j in range(3)]},
            'groups':[{'material':m,'quads':groups[m]} for m in sorted(groups)],'quad_count':sum(len(g) for g in groups.values()),
            'geometry':'Exact full-.05 exposed surfaces, owned/clipped from unchanged common halo meshing. Hidden structural cells use conservative .1 aggregation; no core faces are visible.',
            'provenance':{'sampling_backend':sampler_provenance,'prepared_plans':plan_identity,'compiler_source_hash':a.sha(a.core.__file__),'layer_engine_sha256':a.sha(__file__),'layer_rules_sha256':a.sha(rules_path),
                          'exporter_sha256':a.sha(sys.modules[make_render_data.__module__].__file__),'fine_face_fingerprint':face_fp.value(),
                          'mixed_occupancy_pitches_m':[.05,.1],'core_visible_faces':0,'storage_mode':header['storage_mode'],'payload_hash_kind':'fine_occupancy_fingerprint_certificate' if render_only else 'compressed_cells_file_sha256'}}
        if checkpoint_enabled and time.perf_counter()-start>=policy['soft_stop_seconds']:return stop_checkpoint()
        with partial['.render.json'].open('wb',buffering=0) as raw:
            with gzip.GzipFile(filename='',mode='wb',fileobj=BudgetedWriter(raw),mtime=0,compresslevel=5) as compressed:
                with io.TextIOWrapper(compressed,encoding='utf-8') as stream:json.dump(render,stream,separators=(',',':'),ensure_ascii=False);stream.write('\n')
        size=sum(partial[k].stat().st_size for k in active_file_keys)
        a.fail(used+size<=rules['total_output_budget_bytes'],'layer_output_disk_budget_exceeded',{'used':used,'new':size,'limit':rules['total_output_budget_bytes']})
        stats={'schema':'riverstone.house_detail.layered_stats.v1','status':'PASS_STRUCTURAL_PENDING_VISUAL','asset_key':asset_key,'render_encoding':'gzip_json','render_gzip_mtime':0,
               'source_master_sha256':record['source_sha256'],'authored_master_sha256':record['emitted_master_sha256'],
               'full_fine_fingerprint':all_fp.value(),'fine_face_fingerprint':face_fp.value(),
               'reference_full_fine_cells':all_fp.count,'stored_fine_cells':total_fine,'stored_core_cells':total_core,
               'stored_total_cells':total_fine+total_core,'lossless_fine_expanded_cell_count':total_fine+8*total_core,
               'quads':render['quad_count'],'visible_unit_faces':face_fp.count,'core_visible_faces':0,
               'chunks':chunk_stats,'candidate_cells_including_halos':candidate_total,'elapsed_seconds':prior_elapsed+time.perf_counter()-start,'authoring_seed':header.get('authoring_seed'),'connectivity_source_sha256':header['connectivity_source_sha256'],
               'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'memory_limit_bytes':effective_memory_limit,'wall_time_limit_seconds':wall_limit,'chunk_enumeration':chunk_plan,
               'constraints':checks,'source_unchanged':a.sha(source_path)==record['source_sha256'],'compiler_changed':True,'compiler_extension':'opt_in_immutable_prepared_sampling_v3_with_integer_cell_bounds_v1','sampling_backend':sampler_provenance,'compiler_default_geometry_unchanged':True,'previous_compiler_sha256':'c4cc126554425211c7c670fefd0f97c22534ee5e489886354e0e00dd913f19e6',
               'full_building_cell_merge_created':False,'geometry_fallback':False,'mixed_occupancy_pitches_m':[.05,.1],
               'spatial_sampling_contract':'original_shapes_integer_cell_bounds_v1','op_pruning_mode':'full_original_master_immutable_plan_integer_range_intersection','prepared_plans':plan_identity,'prepared_plan_metrics':plan_metrics,
               'polygon_predicate_guard':{'used':False,'reason':'Original shape and polygon predicates are never cropped; only integer sample ranges are bounded.'},
               'all_chunks_exact_exterior_face_match':True,'all_chunks_overlap_free':True,'fine_grid_vertex_rounding_decimals':rules['vertex_decimal_places'],
               'files':{},'budget_scope':str(budget_root.relative_to(a.ROOT)),'budget_used_before_bytes':used,'storage_mode':header['storage_mode'],'retained_cell_payload':not render_only}
        if checkpoint_enabled:
            execution_ledger['sessions'][-1].update(status='COMPLETED_SAMPLING',elapsed_seconds=time.perf_counter()-start,completed_chunks=checkpoint.completed_count)
            commit_checked(ledger_path,execution_ledger)
            stats['checkpoint']={'directory':str(checkpoint_path.relative_to(a.ROOT)),'committed_chunks':checkpoint.completed_count,
                'resumed_chunks':resume_start,'sessions_started':sessions_started,'max_sessions':policy['max_sessions'],
                'per_session_wall_seconds':wall_limit,'max_total_execution_budget_seconds':policy['max_sessions']*wall_limit,
                'retained_cell_arrays':False,'completed_checkpoints_preserved':True,'policy_sha256':a.sha(policy_path),
                'elapsed_scope':'Sum of prior committed checkpoint time and current execution; interrupted incomplete work is excluded.',
                'execution_ledger_path':str(ledger_path.relative_to(a.ROOT)),'execution_records':copy.deepcopy(execution_ledger['sessions'])}
        if render_only:
            stats['compiled_header']=header;stats['occupancy_certificate_sha256']=gzip_sha
            snapshot_growth=0
            for role,path in replay_paths.items():
                path=Path(path);snapshot=HERE/'replay_code'/(role+'_'+a.sha(path)[:16]+path.suffix)
                if not snapshot.exists():snapshot_growth+=path.stat().st_size
            reserve_bytes(snapshot_growth)
            stats['replay_contract']=render_only_retention.preserve_replay_sources(a,HERE,asset_key,master_path,source_path,catalog_path,rules_path,replay_paths)
            stats['replay_contract']['command'][1]=str(Path(__file__).resolve().relative_to(a.ROOT))
            stats['replay_contract']['sampling_backend']=sampler_provenance
            stats['replay_contract']['prepared_plans']=plan_identity
            stats['replay_contract']['independent_certificate_backend']='preserved_reference_core.compile_master'
            if checkpoint_enabled:
                stats['replay_contract']['command'].extend(['--checkpoint-policy',str(policy_path.relative_to(a.ROOT))])
                stats['replay_contract']['checkpoint_resume']={'soft_exit_code':75,'resume_argument':'--resume-checkpoint',
                    'max_sessions':2,'per_session_wall_seconds':900,'soft_stop_seconds':policy['soft_stop_seconds']}
        stats['output_reservation']={**header['output_reservation'],'state':'ACTIVE_UNTIL_FINAL_QA','shared_usage_before_commit':book.inspect()}
        for key in active_file_keys:
            partial[key].rename(paths[key]);stats['files'][key]={'path':str(paths[key].relative_to(a.ROOT)),'bytes':paths[key].stat().st_size,'sha256':a.sha(paths[key]),'encoding':'gzip_json' if key=='.render.json' else 'gzip_jsonl'}
        reserve_bytes(len(encoded_json(stats)));a.write(partial['.stats.json'],stats)
        actual_stored_bytes=sum(p.stat().st_size for root in budget_roots for p in root.rglob('*') if p.is_file())+sum(p.stat().st_size for p in (HERE/'replay_code').rglob('*') if p.is_file())
        a.fail(actual_stored_bytes+2048<=rules['total_output_budget_bytes'],'layer_final_artifact_budget_exceeded',{'bytes':actual_stored_bytes,'limit':rules['total_output_budget_bytes']})
        os.replace(partial['.stats.json'],paths['.stats.json'])
        if checkpoint_enabled:
            checkpoint.mark_complete(paths['.stats.json'],a.sha(paths['.stats.json']),budget_check=reserve_bytes)
            execution_ledger['sessions'][-1].update(status='COMPLETE',elapsed_seconds=time.perf_counter()-start,
                final_stats_path=str(paths['.stats.json'].relative_to(a.ROOT)),final_stats_sha256=a.sha(paths['.stats.json']))
            commit_checked(ledger_path,execution_ledger)
        progress.update(status='COMPLETE',stats_path=str(paths['.stats.json'].relative_to(a.ROOT)),stats_sha256=a.sha(paths['.stats.json']),
            seconds=stats['elapsed_seconds'],max_rss_kib=stats['max_rss_kib'])
        commit_checked(progress_path,progress)
        print(json.dumps({k:v for k,v in stats.items() if k!='chunks'}),flush=True)
        return stats
    except (MemoryError,a.core.BudgetExceeded,a.UnsupportedSurface,ValueError,TimeoutError) as error:
        report={'status':'PENDING_NO_FALLBACK','asset_key':asset_key,'error':type(error).__name__,'reason':str(error),
                'elapsed_seconds':time.perf_counter()-start,'completed_chunks':len(chunk_stats),'durable_checkpoint_chunks':checkpoint.completed_count if checkpoint else None,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'partial_files':[str(p.relative_to(a.ROOT)) for p in partial.values() if p.exists()],'progress_path':str(progress_path.relative_to(a.ROOT)) if progress_path.exists() else None}
        if isinstance(error,a.UnsupportedSurface):report['details']=error.report
        failure_path=output/(asset_key+'.layered.blocked.json')
        suffix=1
        while failure_path.exists():
            suffix+=1;failure_path=output/(asset_key+'.layered.blocked.resume_'+str(suffix)+'.json')
        reserve_bytes(len(encoded_json(report)),emergency=True);a.write(failure_path,report)
        if session_registered:
            execution_ledger['sessions'][-1].update(status='FAILED_PRESERVED',elapsed_seconds=time.perf_counter()-start,
                failure_path=str(failure_path.relative_to(a.ROOT)))
            commit_checked(ledger_path,execution_ledger,emergency=True)
        print(json.dumps(report),flush=True)
        raise
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,previous_alarm)
        book.release_writer(reservation_key)
        fcntl.flock(lock,fcntl.LOCK_UN);lock.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('asset_key');parser.add_argument('--output-dir',type=Path);parser.add_argument('--rules',type=Path);parser.add_argument('--catalog',type=Path);parser.add_argument('--render-only',action='store_true')
    parser.add_argument('--checkpoint-policy',type=Path);parser.add_argument('--resume-checkpoint',action='store_true')
    args=parser.parse_args();result=run(args.asset_key,args.output_dir,args.rules,args.catalog,args.render_only,args.checkpoint_policy,args.resume_checkpoint)
    if result.get('status')=='PENDING_RESUMABLE_CHECKPOINT':raise SystemExit(75)
    if result.get('status')=='PENDING_CHECKPOINT_SESSION_LIMIT':raise SystemExit(76)
