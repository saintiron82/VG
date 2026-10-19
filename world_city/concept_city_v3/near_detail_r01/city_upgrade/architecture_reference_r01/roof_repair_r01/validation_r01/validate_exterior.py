#!/usr/bin/env python3
"""Independent exact unit-face audit using one material plane at a time.

Never compiles, samples continuous shapes, meshes, or expands the full house.
All authored faces are checked on the common .0625m integer lattice. Material
IDs -1 denote empty space. Baseline .125m cells are queried virtually by //2.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2)
_cpu_hard=resource.getrlimit(resource.RLIMIT_CPU)[1]
_cpu_cap=120 if _cpu_hard==resource.RLIM_INFINITY else min(120,_cpu_hard)
resource.setrlimit(resource.RLIMIT_CPU,(_cpu_cap,)*2)
import argparse, gzip, hashlib, json, math, re, time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
R=HERE.parent
ARCH=R.parent
ROOT=next(p for p in HERE.parents if (p/'voxel_character/common/core.py').exists())
PITCH=.0625

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()

def ref(path):return {'path':str(Path(path).relative_to(ROOT)),'sha256':sha(path)}
def read(path):
    path=Path(path)
    with gzip.open(path,'rt') if path.name.endswith('.gz') else path.open() as f:return json.load(f)
def save(path,data):Path(path).write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n')
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def nonzero(a):return sum(x!=0 for x in a)

class BaselineOracle:
    """Finite baseline array queried in integer .0625m world coordinates."""
    def __init__(self,arrays):
        a=np.load(arrays)
        self.mats=np.where(a['occupancy'],a['materials'],-1).astype(np.int16)
        self.low=(-96,0,-80);self.high=(96,224,80)
    def values(self,x,y,z):
        shape=np.broadcast_shapes(x.shape,y.shape,z.shape)
        x,y,z=np.broadcast_arrays(x,y,z)
        out=np.full(shape,-1,np.int16)
        ix=x//2+48;iy=y//2;iz=z//2+40
        ok=(ix>=0)&(ix<96)&(iy>=0)&(iy<112)&(iz>=0)&(iz<80)
        out[ok]=self.mats[iy[ok],ix[ok],iz[ok]]
        return out
    def plane(self,axis,pos,low=None,high=None):
        low=self.low if low is None else low;high=self.high if high is None else high
        u,v=[i for i in range(3) if i!=axis]
        shape=[1,1];coords=[None]*3
        coords[axis]=np.asarray(pos)
        coords[u]=np.arange(low[u],high[u],dtype=np.int32)[:,None]
        coords[v]=np.arange(low[v],high[v],dtype=np.int32)[None,:]
        return self.values(*coords)

def index_faces(render,material_ids,low,high,triangle_order):
    assert render['schema']=='riverstone.voxel.render.v1'
    assert render['unit']=='m'
    index={};quad_count=0;triangles=0;area=0
    for group in render['groups']:
        material=group['material'];assert material in material_ids,'Unknown render material'
        for q in group['quads']:
            assert len(q)==4 and all(len(p)==3 for p in q),'Quad shape'
            assert all(type(n) in (int,float) and math.isfinite(n) for p in q for n in p),'Nonfinite quad'
            g=[[round(n/PITCH) for n in p] for p in q]
            assert all(abs(g[i][j]*PITCH-q[i][j])<1e-9 for i in range(4) for j in range(3)),'Off-grid quad'
            lo=[min(p[a] for p in g) for a in range(3)];hi=[max(p[a] for p in g) for a in range(3)]
            fixed=[a for a in range(3) if lo[a]==hi[a]]
            assert len(fixed)==1,'Not a nondegenerate axis-aligned quad'
            axis=fixed[0];u,v=[a for a in range(3) if a!=axis]
            assert len({tuple(p) for p in g})==4,'Duplicate quad vertex'
            assert {(p[u],p[v]) for p in g}=={(a,b) for a in [lo[u],hi[u]] for b in [lo[v],hi[v]]},'Rectangle corners'
            assert all(nonzero(sub(g[(i+1)%4],g[i]))==1 for i in range(4)),'Bow-tie or diagonal rectangle edge'
            n=cross(sub(g[1],g[0]),sub(g[2],g[0]));n2=cross(sub(g[2],g[0]),sub(g[3],g[0]))
            assert n==n2 and nonzero(n)==1,'Inconsistent CCW triangulation'
            sign=1 if n[axis]>0 else -1
            for a,b,c in [triangle_order[:3],triangle_order[3:]]:
                assert cross(sub(g[b],g[a]),sub(g[c],g[a]))==tuple(-x for x in n),'Godot triangle winding not reversed'
                triangles+=1
            assert all(low[a]<=lo[a]<=hi[a]<=high[a] for a in range(3)),'Face outside oracle bounds'
            rectangle=(lo[u]-low[u],lo[v]-low[v],hi[u]-low[u],hi[v]-low[v],material_ids[material])
            index.setdefault((axis,lo[axis],sign),[]).append(rectangle)
            quad_count+=1;area+=(hi[u]-lo[u])*(hi[v]-lo[v])
    assert quad_count==render['quad_count'],'Incorrect quad_count'
    return index,{'quads_checked':quad_count,'godot_reversed_triangles_checked':triangles,'render_unit_face_writes':area}

def audit_render(render,oracle,material_ids,triangle_order,interface_y=152,extra_interfaces=()):
    low,high=oracle.low,oracle.high
    faces,report=index_faces(render,material_ids,low,high,triangle_order)
    report.update(expected_unit_faces=0,same_direction_duplicate_unit_faces=0,missing_unit_faces=0,extraneous_unit_faces=0,wrong_material_unit_faces=0,artificial_interface_unit_faces=0,planes_checked=0)
    examples=[]
    interfaces={(1,interface_y),*extra_interfaces}
    seam_report={f'{a}:{p}':{'missing':0,'extraneous':0,'wrong_material':0} for a,p in sorted(interfaces)}
    for axis in range(3):
        previous=oracle.plane(axis,low[axis]-1)
        for position in range(low[axis],high[axis]+1):
            current=oracle.plane(axis,position)
            for sign,owner,neighbor in ((1,previous,current),(-1,current,previous)):
                expected=np.where((owner>=0)&(neighbor<0),owner,-1)
                actual=np.full(expected.shape,-1,np.int16)
                for u0,v0,u1,v1,material in faces.pop((axis,position,sign),[]):
                    target=actual[u0:u1,v0:v1]
                    report['same_direction_duplicate_unit_faces']+=int(np.count_nonzero(target>=0))
                    target[:]=material
                missing=(expected>=0)&(actual<0);extra=(expected<0)&(actual>=0);wrong=(expected>=0)&(actual>=0)&(expected!=actual)
                report['expected_unit_faces']+=int(np.count_nonzero(expected>=0))
                for key,mask in [('missing_unit_faces',missing),('extraneous_unit_faces',extra),('wrong_material_unit_faces',wrong)]:
                    count=int(np.count_nonzero(mask));report[key]+=count
                    if count and len(examples)<12:
                        uv=np.argwhere(mask)[0].tolist();examples.append({'failure':key,'axis':axis,'plane':position,'sign':sign,'plane_uv_index':uv,'expected_material':int(expected[tuple(uv)]),'actual_material':int(actual[tuple(uv)])})
                if axis==1 and position==interface_y:report['artificial_interface_unit_faces']+=int(np.count_nonzero(extra))
                if (axis,position) in interfaces:
                    seam=seam_report[f'{axis}:{position}']
                    for label,mask in [('missing',missing),('extraneous',extra),('wrong_material',wrong)]:seam[label]+=int(np.count_nonzero(mask))
                report['planes_checked']+=1
            previous=current
    assert not faces,'Unvisited face planes'
    report['outward_CCW_matches_actual_solid_exterior']=all(report[k]==0 for k in ('same_direction_duplicate_unit_faces','missing_unit_faces','extraneous_unit_faces','wrong_material_unit_faces'))
    report['failure_examples']=examples
    report['interface_planes']=seam_report
    return report

def adapter_order():
    adapter=ROOT/'world_city/concept_city_v3/playable_detail_r01/RenderData.gd'
    match=re.search(r'const TRIANGLE_ORDER\s*:?=\s*(\[[^\]]+\])',adapter.read_text())
    assert match,'Actual Godot adapter triangle order missing'
    order=json.loads(match.group(1));assert order==[0,2,1,0,3,2]
    return adapter,order

def baseline_audit():
    started=time.monotonic();base=ARCH/'foundation_repair_r01'
    oracle=BaselineOracle(base/'foundation_arrays.npz')
    render=read(base/'foundation_repaired.render.json.gz')
    material_ids={**{f'pixel_{i:02d}':i for i in range(12)},**{f'stone_pixel_{i:02d}':i+12 for i in range(3)}}
    adapter,order=adapter_order()
    report=audit_render(render,oracle,material_ids,order)
    report.update(schema='riverstone.roof_repair.independent_baseline_face_audit.v1',source_arrays=ref(base/'foundation_arrays.npz'),source_render=ref(base/'foundation_repaired.render.json.gz'),godot_adapter=ref(adapter),validator=ref(Path(__file__)),sampling_calls=0,mesher_calls=0,full_house_fine_volume_allocated=False,address_space_limit_mib=256,elapsed_seconds=time.monotonic()-started,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    save(HERE/'baseline_exterior_audit.json',report)
    print(json.dumps(report,sort_keys=True))
    assert report['outward_CCW_matches_actual_solid_exterior']

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
    if args.baseline:baseline_audit()
