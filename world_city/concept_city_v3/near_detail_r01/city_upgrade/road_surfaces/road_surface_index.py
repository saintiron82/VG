"""Read-only public paving eligibility, indexed into original 88-byte city faces.

No global module placements, copied city mesh, collider edits or height sampler.
Public semantics and exact finite triangle footprint are separate requirements.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
import mmap
from pathlib import Path
import struct
import sys
import time

import numpy as np

sys.dont_write_bytecode=True

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
CITY=ROOT/'world_city/concept_city_v3'
INDEX_PATH=CITY/'playable_r01/generated/tile_r01/index.json'
sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as polygons
from world_city.concept_city_v3.registered_source.geometry import triangulate

DTYPE=np.dtype([('vertices','<f8',(3,3)),('source_kind','<u4'),('material_index','<u4'),('source_triangle_index','<u4'),('replacement_index','<u4')])
RECORD=struct.Struct('<9d4I')
EPS=1e-8
MAX_GRADE=.25
MAX_BYTES=8000000


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_bytes())


def checked_ref(reference):
    p=(ROOT/reference['path']).resolve()
    if not p.is_relative_to(ROOT.resolve()) or sha(p)!=reference['sha256']:raise ValueError('source identity mismatch: '+reference['path'])
    return p


def scene_header(path):
    # The pinned scene's first large field is surfaces. Read its 6 MB metadata
    # prefix rather than expanding the entire 194 MB scene into Python objects.
    with Path(path).open('rb') as f:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
            end=data.find(b',"surfaces":')
            if not 0<end<16000000:raise ValueError('unrecognized bounded source header')
            value=json.loads(data[:end]+b'}')
    if 'terrain_contract' not in value or 'materials' not in value:raise ValueError('source header is incomplete')
    return value


def bb(poly):return [min(v[0] for v in poly),min(v[1] for v in poly),max(v[0] for v in poly),max(v[1] for v in poly)]
def overlap(a,b):return min(a[2],b[2])>=max(a[0],b[0])-EPS and min(a[3],b[3])>=max(a[1],b[1])-EPS


class DomainIndex:
    def __init__(self,domains,cell=16):
        self.domains=domains;self.cell=cell;self.grid=defaultdict(list)
        for i,d in enumerate(domains):
            for key in self.cells(bb(d['polygon_xz_m'])):self.grid[key].append(i)
    def cells(self,bounds):
        for x in range(math.floor(bounds[0]/self.cell),math.floor(bounds[2]/self.cell)+1):
            for z in range(math.floor(bounds[1]/self.cell),math.floor(bounds[3]/self.cell)+1):yield x,z
    def candidates(self,poly,material):
        bounds=bb(poly);found=set()
        for key in self.cells(bounds):found.update(self.grid.get(key,()))
        return [self.domains[i] for i in sorted(found) if self.domains[i]['material']==material and overlap(bounds,self.domains[i]['bounds'])]


def make_domains(header):
    contract=header['terrain_contract'];roads={r['id']:r for r in contract['roads']}
    roads.update({r['id']:r for r in contract.get('replaced_roads',[])})
    domains=[];owners=[]
    for ident,road in sorted(roads.items()):
        owner=len(owners);owners.append({'id':ident,'kind':'source_registered_public_road','material':'road','source':'base_scene.terrain_contract.roads/replaced_roads','width_m':road['width_m']})
        half=road['width_m']/2
        for i,(a,b) in enumerate(zip(road['polyline_xz_m'],road['polyline_xz_m'][1:])):
            length=math.dist(a,b)
            if length<=1e-7:continue
            n=[-(b[1]-a[1])*half/length,(b[0]-a[0])*half/length]
            poly=[[a[0]+n[0],a[1]+n[1]],[b[0]+n[0],b[1]+n[1]],[b[0]-n[0],b[1]-n[1]],[a[0]-n[0],a[1]-n[1]]]
            domains.append({'owner':owner,'material':'road','polygon_xz_m':poly,'bounds':bb(poly),'segment':i})
    southern=contract.get('south_country_road',{})
    if southern:
        owner=len(owners);owners.append({'id':southern['route_id'],'kind':'source_finite_public_country_road','material':'road','source':'base_scene.terrain_contract.south_country_road'})
        for row in southern['triangles']:
            poly=row['polygon_xz_m'];domains.append({'owner':owner,'material':'road','polygon_xz_m':poly,'bounds':bb(poly)})
    market=[r for r in contract['terrace_regions'] if r['id']=='MARKET']
    if len(market)!=1:raise ValueError('unique exact MARKET source owner required')
    owner=len(owners);owners.append({'id':'MARKET','kind':'source_market_civic_terrace','material':'space_civic','source':'base_scene.terrain_contract.terrace_regions','floor_y_m':market[0]['floor_y_m']})
    for poly in triangulate(market[0]['polygon_xz_m']):domains.append({'owner':owner,'material':'space_civic','polygon_xz_m':poly,'bounds':bb(poly)})
    return owners,domains


def geometry_check(vertices,max_grade=MAX_GRADE):
    v=np.asarray(vertices,dtype=float);n=np.cross(v[1]-v[0],v[2]-v[0]);length=float(np.linalg.norm(n))
    if not np.isfinite(v).all() or not length>1e-12:return None,'degenerate_or_nonfinite'
    if n[1]<=1e-10:return None,'not_upward_top'
    grade=float(math.hypot(n[0],n[2])/n[1])
    if grade>max_grade:return None,'excessive_grade_or_riser'
    f=v.astype(np.float32);fn=np.cross(f[1]-f[0],f[2]-f[0])
    if float(np.dot(n,fn))<=0:return None,'float32_winding_unstable'
    if abs(float(n[1]))/2<1e-8:return None,'tiny_projected_area'
    a,b=-float(n[0]/n[1]),-float(n[2]/n[1]);c=float(v[0,1]-a*v[0,0]-b*v[0,2])
    return {'plane_y_xz_m':[a,b,c],'normal':(n/length).tolist(),'grade':grade,'projected_area_m2':float(n[1])/2},None


def domain_owners(poly,material,domains):
    candidates=domains.candidates(poly,material)
    # First try a containing convex strip; otherwise exact union subtraction.
    for d in candidates:
        if polygons.convex_polygon_contains(d['polygon_xz_m'],poly,0):return [d['owner']]
    if not candidates:return []
    covers=[d['polygon_xz_m'] for d in candidates]
    if polygons.uncovered_area_by_union(poly,covers,0)>1e-7:return []
    return sorted({d['owner'] for d in candidates if polygons.intersection_area(poly,d['polygon_xz_m'])>1e-10})


def encode_runs(rows):
    result=[]
    for face,owners in rows:
        if result and result[-1][1]==face and result[-1][2]==owners:result[-1][1]=face+1
        else:result.append([face,face+1,owners])
    return result


def build(output=HERE/'generated'):
    output=Path(output).resolve()
    if not output.is_relative_to(HERE):raise ValueError('write only within road_surfaces')
    start=time.perf_counter();source=read(INDEX_PATH)
    if len(source['tiles'])!=360 or source['binary_layout'].get('stride_bytes')!=88:raise ValueError('unexpected city source layout')
    base=checked_ref(source['sources']['base_scene']);header=scene_header(base)
    plan=ROOT/header['source_plan']
    if sha(plan)!=header['source_plan_sha256']:raise ValueError('source road plan mismatch')
    owners,domains=make_domains(header);domain_index=DomainIndex(domains)
    materials=source['material_ids'];counts=Counter();geometry_counts=Counter();owner_counts=Counter();tiles={};native_stairs=[];native_public_candidates=[]
    for tid,tile in source['tiles'].items():
        binary=checked_ref({'path':tile['terrain_path'],'sha256':tile['terrain_sha256']})
        companion=checked_ref({'path':tile['instances_path'],'sha256':tile['instances_sha256']})
        data=np.fromfile(binary,dtype=DTYPE);meta=read(companion)
        if len(data)!=tile['face_count']:raise ValueError('wrong face count')
        skip=set(meta.get('render_skip_indices',[]));selected=[];by_material=Counter();rejected=Counter()
        for mi,material in enumerate(materials):counts['source/'+material]+=int(np.sum(data['material_index']==mi))
        candidates=np.flatnonzero(np.isin(data['material_index'],[materials.index('road'),materials.index('space_civic')]))
        for fi in candidates:
            fi=int(fi);row=data[fi];material=materials[int(row['material_index'])]
            if fi in skip:rejected['render_duplicate']+=1;continue
            geometry,reason=geometry_check(row['vertices'])
            if reason:rejected[reason]+=1;continue
            poly=row['vertices'][:,[0,2]].tolist();matched=domain_owners(poly,material,domain_index)
            if not matched:rejected['no_complete_public_owner_footprint']+=1;continue
            selected.append((fi,matched));by_material[material]+=1
            geometry_counts['flat' if geometry['grade']<1e-7 else 'sloped']+=1
            for owner in matched:owner_counts[owners[owner]['id']]+=1
        for k,n in rejected.items():counts['rejected/'+k]+=n
        for k,n in by_material.items():counts['selected/'+k]+=n
        for p in meta.get('common_instances',[]):
            words=(p.get('id','')+' '+p.get('asset_key','')).lower()
            if any(s in words for s in ['stair','fine_access','pedestrian_step']):native_stairs.append({'tile_id':tid,'id':p['id'],'asset_key':p['asset_key'],'status':'NOT_SELECTED_NATIVE_PUBLIC_OWNERSHIP_AND_TREAD_ADAPTER_REQUIRED'})
            elif 'public' in words:native_public_candidates.append(p['id'])
        tiles[tid]={'face_count':tile['face_count'],'source_binary_sha256':tile['terrain_sha256'],'source_companion_sha256':tile['instances_sha256'],'eligible_face_runs':encode_runs(selected),'eligible_face_count':len(selected),'selected_material_counts':dict(by_material),'rejected_counts':dict(rejected)}
    index={'schema':'riverstone.public_paving.source_index.v1','source_tile_index':{'path':str(INDEX_PATH.relative_to(ROOT)),'sha256':sha(INDEX_PATH)},'source_scene':source['sources']['base_scene'],'source_plan':{'path':header['source_plan'],'sha256':header['source_plan_sha256']},
           'source_material_policy_code':{'path':'world_city/concept_city_v3/registered_topography/revisions/r12_boundary_diagnostics/materials.py','sha256':sha(CITY/'registered_topography/revisions/r12_boundary_diagnostics/materials.py')},
           'safe_paving_manifest':{'path':str((HERE.parent/'surface_modules/generated_safe/manifest.json').relative_to(ROOT)),'sha256':sha(HERE.parent/'surface_modules/generated_safe/manifest.json')},
           'owners':owners,'tiles':tiles,'policy':{'candidate_materials':['road','space_civic'],'owner_footprint_required':True,'unmatched_owner_policy':'exclude','world_coordinates':'preserve original float64 triangles; no height resampling','maximum_grade':MAX_GRADE,'visual_offset_along_normal_m':.0375,'preserve_collision':True,'copy_geometry_globally':False,'module_generation':'observer bounded only; complete same-plane footprint support required','stairs':'native stairs not selected; collision-contract triangles are never visual paving input','rle':'[first_face_index,exclusive_end_face_index,owner_indices]'},'whole_city_coverage_pass':False}
    report={'status':'SOURCE_SELECTION_VALIDATED_RUNTIME_INTEGRATION_PENDING','all_source_tiles_read_and_hash_verified':len(tiles),'all_source_faces_read':sum(t['face_count'] for t in tiles.values()),'counts':dict(counts),'eligible_faces':sum(t['eligible_face_count'] for t in tiles.values()),'eligible_geometry':dict(geometry_counts),'owners_with_selected_faces':dict(owner_counts),'native_stair_candidates':native_stairs,'native_public_name_only_not_selected':native_public_candidates,'not_covered':['Unmatched public-route caps, restored/appended corridors outside pinned owner footprints','Private or ambiguous alley and ground_stone faces','Native public stairs and stair/bridge collision-only profiles','Other precinct plazas without explicit approved public paving owner'],'whole_city_coverage_pass':False,'elapsed_seconds':round(time.perf_counter()-start,3)}
    output.mkdir(exist_ok=True,parents=True)
    for name,value in [('source_index.json',index),('selection_report.json',report)]:
        text=(json.dumps(value,separators=(',',':'),sort_keys=True)+'\n').encode()
        if len(text)>MAX_BYTES:raise ValueError('8 MB artifact budget exceeded')
        path=output/name
        if path.exists() and name!='selection_report.json' and path.read_bytes()!=text:raise ValueError('existing changed index preserved; use new output directory')
        path.write_bytes(text)
    print(json.dumps({'eligible_faces':report['eligible_faces'],'counts':dict(counts),'geometry':dict(geometry_counts),'bytes':sum(p.stat().st_size for p in output.iterdir()),'seconds':report['elapsed_seconds']}),flush=True)
    return index,report


def decode_face(binary,index):
    values=RECORD.unpack_from(binary,index*88)
    return [list(values[j:j+3]) for j in (0,3,6)],list(values[9:])


def query_sources(selection,observer_xyz,radius_m=10,max_faces=8192):
    """Bounded runtime reference: original faces, no fine module generation."""
    if not 0<radius_m<=12 or not 1<=max_faces<=20000:raise ValueError('bounded query required')
    if len(observer_xyz)!=3 or not all(math.isfinite(v) for v in observer_xyz):raise ValueError('finite observer required')
    source=read(checked_ref(selection['source_tile_index']));x,y,z=observer_xyz
    region=[x-radius_m,z-radius_m,x+radius_m,z+radius_m];wanted=set()
    for ix in range(math.floor(region[0]/64),math.floor(region[2]/64)+1):
        for iz in range(math.floor(region[1]/64),math.floor(region[3]/64)+1):
            tile=source['tiles'].get(f'{ix}_{iz}')
            if tile:wanted.add(tile['id']);wanted.update(tile['dependency_owner_tiles'])
    faces=[]
    for tid in sorted(wanted):
        selected=selection['tiles'][tid];tile=source['tiles'][tid]
        if not selected['eligible_face_count']:continue
        blob=checked_ref({'path':tile['terrain_path'],'sha256':selected['source_binary_sha256']}).read_bytes()
        for first,end,owners in selected['eligible_face_runs']:
            for fi in range(first,end):
                vertices,provenance=decode_face(blob,fi);poly=[[v[0],v[2]] for v in vertices]
                if not overlap(bb(poly),region):continue
                g,reason=geometry_check(vertices)
                if reason:raise ValueError('indexed face now violates geometry contract')
                if min(abs(v[1]-y) for v in vertices)>3:continue
                faces.append({'tile_id':tid,'face_index':fi,'source_provenance':provenance,'owners':owners,'vertices_xyz_m':vertices,**g})
                if len(faces)>=max_faces:return {'faces':faces,'truncated':True,'radius_m':radius_m,'whole_city_coverage_pass':False}
    return {'faces':faces,'truncated':False,'radius_m':radius_m,'whole_city_coverage_pass':False}


def rigid_frame(plane):
    """Proper orthonormal XY/+Z surface frame, with source-plane origin."""
    a,b,c=plane;n=np.asarray([-a,1,-b],dtype=float);n/=np.linalg.norm(n)
    u=np.asarray([1,a,0],dtype=float);u/=np.linalg.norm(u);v=np.cross(n,u)
    return np.column_stack([u,v,n]),np.asarray([0,c,0],dtype=float)


def footprint_supported(corners_xyz,faces,tolerance=1e-6):
    """Exact finite union; never bridge a hole, different plane or stair riser."""
    if len(corners_xyz)!=4 or not faces:return False
    corners=np.asarray(corners_xyz,dtype=float)
    if not np.isfinite(corners).all():return False
    plane=faces[0]['plane_y_xz_m'];a,b,c=plane
    if max(abs(p[1]-(a*p[0]+b*p[2]+c)) for p in corners)>tolerance:return False
    subject=corners[:,[0,2]].tolist();bounds=bb(subject);covers=[]
    for f in faces:
        vertices=f['vertices_xyz_m']
        if max(abs(v[1]-(a*v[0]+b*v[2]+c)) for v in vertices)>tolerance:continue
        polygon=[[v[0],v[2]] for v in vertices]
        if overlap(bounds,bb(polygon)):covers.append(polygon)
    return bool(covers) and polygons.uncovered_area_by_union(subject,covers,0)<=1e-8


def plan_local_modules(faces,observer_xyz,radius_m=8,max_modules=256,module_sizes=(1.0,.5,.25),max_candidate_checks=8192):
    """Conservative bounded reference planner. Output is ephemeral, never global.

    Planes are not averaged. Different grades/heights cannot jointly support a
    module. Small rectangle trims are selected only inside the exact source union.
    """
    if not 0<radius_m<=12 or not 1<=max_modules<=1024:raise ValueError('bounded module request required')
    if not 1<=max_candidate_checks<=32768:raise ValueError('bounded candidate checks required')
    if not set(module_sizes)<=set((1.0,.75,.5,.25)):raise ValueError('only reviewed aligned trims')
    groups=defaultdict(list)
    for f in faces:
        p=f['plane_y_xz_m'];groups[tuple(round(v,7 if i<2 else 6) for i,v in enumerate(p))].append(f)
    result=[];spent=set();observer=np.asarray(observer_xyz,dtype=float);checks=0
    ordered=sorted(groups.values(),key=lambda fs:min(np.linalg.norm(np.asarray(v)-observer) for f in fs for v in f['vertices_xyz_m']))
    for group in ordered:
        frame,origin=rigid_frame(group[0]['plane_y_xz_m']);local=(observer-origin)@frame
        local_vertices=(np.asarray([v for f in group for v in f['vertices_xyz_m']])-origin)@frame
        low=np.maximum(local_vertices.min(axis=0)[:2],local[:2]-radius_m)
        high=np.minimum(local_vertices.max(axis=0)[:2],local[:2]+radius_m)
        for size in module_sizes:
            for ix in range(math.floor(low[0]/size),math.ceil(high[0]/size)):
                for iy in range(math.floor(low[1]/size),math.ceil(high[1]/size)):
                    u,v=ix*size,iy*size
                    trim_offset=[u-math.floor(u),v-math.floor(v)]
                    if any(o+size>1+EPS for o in trim_offset):continue
                    slots={(round((u+i*.25)*4),round((v+j*.25)*4)) for i in range(round(size/.25)) for j in range(round(size/.25))}
                    plane_key=tuple(round(n,7) for n in group[0]['plane_y_xz_m'])
                    if any((plane_key,s) in spent for s in slots):continue
                    local_corners=np.asarray([[u,v,0],[u+size,v,0],[u+size,v+size,0],[u,v+size,0]])
                    corners=local_corners@frame.T+origin
                    if max(math.hypot(q[0]-observer[0],q[2]-observer[2]) for q in corners)>radius_m:continue
                    checks+=1
                    if checks>max_candidate_checks:return {'modules':result,'truncated':True,'reason':'candidate_check_budget','whole_city_coverage_pass':False}
                    if not footprint_supported(corners,group):continue
                    anchor=frame@np.asarray([u,v,.0375])+origin
                    if math.hypot(anchor[0]-observer[0],anchor[2]-observer[2])>radius_m:continue
                    result.append({'kind':'paving','variant_family':'safe_offset_r01','seed':(41873,41879,41887)[(ix*17+iy*31)%3],'width_m':size,'height_m':size,'trim_offset_m':trim_offset,'transform':{'basis':frame.tolist(),'translation':anchor.tolist()},'original_plane_y_xz_m':group[0]['plane_y_xz_m'],'maximum_visual_collision_difference_m':.0375,'collision_change':False,'source_face_refs':[[f['tile_id'],f['face_index']] for f in group if overlap(bb([[q[0],q[2]] for q in f['vertices_xyz_m']]),bb(corners[:,[0,2]].tolist()))]})
                    spent.update((plane_key,s) for s in slots)
                    if len(result)>=max_modules:return {'modules':result,'truncated':True,'whole_city_coverage_pass':False}
    return {'modules':result,'truncated':False,'whole_city_coverage_pass':False}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=HERE/'generated');ap.add_argument('--query',nargs=3,type=float);args=ap.parse_args()
    if args.query:
        selected=read(HERE/'generated/source_index.json');q=query_sources(selected,args.query);print(json.dumps({'face_count':len(q['faces']),'truncated':q['truncated']}))
    else:build(args.output)

if __name__=='__main__':main()
