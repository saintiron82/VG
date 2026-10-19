"""Generic convex source-solid boundary adapter, not a voxel compiler or renderer.

Uses existing common transforms, common greedy cube-face topology, and existing
finite source half-plane clipping. Output is the shared RenderData quad format.
Supports cut-free convex quadrilateral extrusions/boxes under rigid transforms.
"""
from __future__ import annotations
import math
from voxel_character.common import core
from voxel_character.tools.mesh import greedy_faces
from world_city.runtime_city.topography import author as clip

EPS = 1e-8
STENCIL = [corners for corners, _ in greedy_faces([(0, 0, 0, 'surface')])]

def sub(a, b): return [x-y for x,y in zip(a,b)]
def add(a, b): return [x+y for x,y in zip(a,b)]
def mul(a, s): return [x*s for x in a]
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def unit(v): return mul(v, 1/math.sqrt(core.dot(v,v)))
def mean(points): return [sum(p[i] for p in points)/len(points) for i in range(len(points[0]))]

def clean(poly):
    out=clip._clean(poly)
    while len(out)>=3:
        changed=False
        for i in range(len(out)):
            a,b,c=out[i-1],out[i],out[(i+1)%len(out)]
            ab,bc=sub(b,a),sub(c,b)
            if abs(ab[0]*bc[1]-ab[1]*bc[0]) <= EPS*max(math.dist(a,b),math.dist(b,c),1):
                out.pop(i);changed=True;break
        if not changed:break
    return out if len(out)>=3 and abs(clip._area(out))>EPS else []

def solid(record):
    shape=record['shape']; t=core.transform(record.get('transform'))
    if shape['kind']=='box':
        lo,hi=shape['min'],shape['max'];p=[[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]];z0,z1=lo[2],hi[2]
    else:
        assert shape['kind']=='extrusion' and len(shape['polygon'])==4
        p=[list(v) for v in shape['polygon']];z0,z1=shape['z_min'],shape['z_max']
    assert z1>z0 and abs(clip._area(p))>EPS
    if clip._area(p)<0:p.reverse()
    assert all(clip._area([p[i],p[(i+1)%4],p[(i+2)%4]])>EPS for i in range(4)), 'convex source only'
    corner={(0,0):p[0],(1,0):p[1],(1,1):p[2],(0,1):p[3]}
    faces=[]
    for stencil in STENCIL:
        q=[core.apply(t,corner[(v[0],v[1])]+[z0 if v[2]==0 else z1])for v in stencil]
        n=unit(cross(sub(q[1],q[0]),sub(q[2],q[0])))
        faces.append({'q':q,'n':n,'d':core.dot(n,q[0])})
    vertices=[v for f in faces for v in f['q']];center=mean(vertices)
    assert all(core.dot(f['n'],center)<f['d']-EPS for f in faces)
    return {**record,'faces':faces,'bounds':{'min':[min(v[i]for v in vertices)for i in range(3)],'max':[max(v[i]for v in vertices)for i in range(3)]}}

def chart(face):
    o=face['q'][0];u=unit(sub(face['q'][1],o));v=cross(face['n'],u)
    return o,u,v

def project(q,o,u,v): return [[core.dot(sub(p,o),u),core.dot(sub(p,o),v)]for p in q]
def lift(q,o,u,v): return [add(o,add(mul(u,p[0]),mul(v,p[1]))) for p in q]

def regions(solids):
    """Union boundary with later source paint owning coplanar duplicate faces."""
    result=[];removed_area=0.;raw_area=0.
    for i,s in enumerate(solids):
        for fi,face in enumerate(s['faces']):
            o,u,v=chart(face);poly=project(face['q'],o,u,v);pieces=[poly];area=abs(clip._area(poly));raw_area+=area
            for j,other in enumerate(solids):
                if i==j:continue
                if any(max(q[a]for q in face['q'])<other['bounds']['min'][a]-EPS or min(q[a]for q in face['q'])>other['bounds']['max'][a]+EPS for a in range(3)):continue
                # Coincident outer boundary: retain one owner (later source paint).
                same=any(core.dot(face['n'],f['n'])>1-1e-10 and abs(face['d']-f['d'])<EPS for f in other['faces'])
                if same and s['priority']>other['priority']:continue
                planes=[[-core.dot(f['n'],u),-core.dot(f['n'],v),f['d']-core.dot(f['n'],o)]for f in other['faces']]
                # Constant boundary half-planes otherwise duplicate all pieces
                # in shared subtract; zero means on that exact plane, not outside.
                if any(abs(a)+abs(b)<EPS and c < -EPS for a,b,c in planes):continue
                planes=[p for p in planes if abs(p[0])+abs(p[1])>=EPS]
                if not planes:pieces=[];break
                intersection=clip._intersect(poly,planes)
                if not intersection:continue
                pieces=[q for p in pieces for q0 in clip._subtract_convex(p,planes) if (q:=clean(q0))]
                if not pieces:break
            kept=sum(abs(clip._area(p))for p in pieces);removed_area+=area-kept
            for p in pieces:
                result.append({'owner':s['id'],'material':s['material'],'source_face':fi,'n':face['n'],'d':face['d'],'q':lift(p,o,u,v)})
    return result,{'unclipped_source_face_area_m2':raw_area,'removed_internal_or_duplicate_area_m2':removed_area,'boundary_area_m2':raw_area-removed_area,'boundary_regions':len(result)}

def quads(regions):
    groups={};records=[]
    for region in regions:
        p=region['q']
        if len(p)==4:out=[p]
        else:
            c=mean(p);out=[[p[i],mean([p[i],p[(i+1)%len(p)]]),c,mean([p[i-1],p[i]])]for i in range(len(p))]
        for q in out:
            assert core.dot(cross(sub(q[1],q[0]),sub(q[2],q[0])),region['n'])>EPS
            assert core.dot(cross(sub(q[2],q[0]),sub(q[3],q[0])),region['n'])>EPS
            groups.setdefault(region['material'],[]).append(q)
            records.append({**region,'q':q})
    return [{'material':m,'quads':q}for m,q in sorted(groups.items())],records

def area3(face):
    o,u,v=chart(face);return abs(clip._area(project(face['q'],o,u,v)))

def compare_boundaries(left,right):
    """Exact planar domain difference, grouped by material and outward plane."""
    missing=0.
    for f in left:
        o,u,v=chart(f);pieces=[project(f['q'],o,u,v)]
        for other in right:
            if f['material']!=other['material'] or core.dot(f['n'],other['n'])<1-1e-10 or abs(f['d']-other['d'])>EPS:continue
            q=clean(project(other['q'],o,u,v))
            if not q:continue
            if clip._area(q)<0:q.reverse()
            planes=clip._inside_planes(q)
            pieces=[q for p in pieces for q0 in clip._subtract_convex(p,planes) if (q:=clean(q0))]
            if not pieces:break
        missing+=sum(abs(clip._area(p))for p in pieces)
    return missing

def audit_boundary(faces,solids):
    interior_area=0.;duplicate_area=0.;winding_errors=0
    for i,f in enumerate(faces):
        o,u,v=chart(f);p=project(f['q'],o,u,v)
        for other in solids:
            # Strict interior cannot include a boundary that is coplanar with
            # any solid face. All other intersections are checked by exact clips.
            planes=[[-core.dot(x['n'],u),-core.dot(x['n'],v),x['d']-core.dot(x['n'],o)]for x in other['faces']]
            if any(abs(a)+abs(b)<EPS and c<=EPS for a,b,c in planes):continue
            intersection=clip._intersect(p,planes)
            interior_area+=abs(clip._area(intersection)) if intersection else 0.
        for other in faces[i+1:]:
            if abs(core.dot(f['n'],other['n']))<1-1e-10 or abs(core.dot(f['n'],other['q'][0])-f['d'])>EPS:continue
            q=clean(project(other['q'],o,u,v))
            if clip._area(q)<0:q.reverse()
            intersection=clip._intersect(p,clip._inside_planes(q))
            duplicate_area+=abs(clip._area(intersection))if intersection else 0.
        c=mean(f['q']);inside=add(c,mul(f['n'],-1e-6));outside=add(c,mul(f['n'],1e-6))
        contains=lambda p:any(all(core.dot(x['n'],p)<x['d']-1e-9 for x in s['faces'])for s in solids)
        if not contains(inside) or contains(outside):winding_errors+=1
    # Resolve collinear T-junctions before counting undirected boundary edges.
    points={tuple(round(x,9)for x in p):p for f in faces for p in f['q']};edges={}
    for f in faces:
        for a,b in zip(f['q'],f['q'][1:]+f['q'][:1]):
            ab=sub(b,a);length2=core.dot(ab,ab);splits=[(0.,a),(1.,b)]
            for p in points.values():
                t=core.dot(sub(p,a),ab)/length2
                if EPS<t<1-EPS and math.dist(add(a,mul(ab,t)),p)<1e-7:splits.append((t,p))
            splits.sort(key=lambda x:x[0])
            for (_,a1),(_,b1) in zip(splits,splits[1:]):
                ka=tuple(round(x,7)for x in a1);kb=tuple(round(x,7)for x in b1)
                if ka==kb:continue
                key=tuple(sorted((ka,kb)));edges.setdefault(key,[]).append(1 if ka<kb else -1)
    open_edges=[e for e,v in edges.items()if len(v)!=2];bad_winding=[e for e,v in edges.items()if len(v)==2 and sum(v)!=0]
    return {'interior_surface_area_m2':interior_area,'coincident_surface_overlap_m2':duplicate_area,'normal_probe_errors':winding_errors,'open_or_nonmanifold_edge_segments':len(open_edges),'edge_winding_errors':len(bad_winding),'edge_segments_checked':len(edges),'open_edge_examples':open_edges[:5]}
