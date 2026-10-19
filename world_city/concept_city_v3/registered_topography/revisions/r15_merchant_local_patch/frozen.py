"""Read-only frozen R5 triangle queries and exact scene-edit bookkeeping."""
import copy,hashlib,json,math
from pathlib import Path
from . import author as a

SCENE_PATH=a.CITY/'evidence/visual_registered_common_r5/bridge_scene.json'
SCENE_SHA256='a78e1b56bd59b06ec30d4bebec9f6da9d686dca87e6ef87f1d4da181f717a01a'

def canonical_sha(value):
    return hashlib.sha256(json.dumps(value,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def load_scene(path=SCENE_PATH):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SCENE_SHA256:raise ValueError('Changed frozen R5 scene')
    return json.loads(raw)

def bounds(poly):
    return [min(p[0] for p in poly),min(p[1] for p in poly),max(p[0] for p in poly),max(p[1] for p in poly)]

def overlap(b,c):return b[0]<=c[2] and c[0]<=b[2] and b[1]<=c[3] and c[1]<=b[3]

class SurfaceIndex:
    """Index only triangles near source patch windows, without modifying them."""
    def __init__(self,scene,margin=16.):
        windows=[]
        for mask in a.patch_masks():
            b=bounds(mask['polygon_xz_m']);windows.append([b[0]-margin,b[1]-margin,b[2]+margin,b[3]+margin])
        window_index=a.geo._SpatialIndex(32)
        for i,b in enumerate(windows):window_index.add(i,[[b[0],b[1]],[b[2],b[3]]])
        self.records=[];self.index=a.geo._SpatialIndex(8)
        self.source_triangle_count=sum(len(v)//3 for v in scene['surfaces'].values())
        for material,vertices in scene['surfaces'].items():
            if material in ('water','bank'):continue
            for start in range(0,len(vertices),3):
                tri=vertices[start:start+3];poly=[[v[0],v[2]] for v in tri]
                candidates=window_index.candidates(poly)
                if not candidates:continue
                b=bounds(poly)
                if not any(overlap(b,windows[i]) for i in candidates):continue
                if a.geo.polygon_area(poly)<=a.MIN_AREA_M2:continue
                row=dict(material=material,triangle_index=start//3,vertices_xyz_m=tri,
                         polygon_xz_m=poly,plane_y_xz_m=list(a.affine_plane(tri)))
                self.index.add(len(self.records),poly);self.records.append(row)
    def intersecting(self,poly):
        for i in sorted(self.index.candidates(poly)):
            r=self.records[i]
            if a.polygon(a.geo.convex_intersection(poly,r['polygon_xz_m'])):yield r
    def at(self,x,z,tolerance=1e-8):
        return [self.records[i] for i in sorted(self.index.candidates([[x,z]]))
                if a.geo.point_in_convex_polygon([x,z],self.records[i]['polygon_xz_m'],tolerance)]
    def height(self,row,x,z):return a.plane_height(row['plane_y_xz_m'],x,z)
    def edge_knots(self,start,end):
        result=[0.,1.]
        for i in sorted(self.index.candidates([start,end])):
            interval=a.segment_mask_interval(start,end,self.records[i]['polygon_xz_m'])
            if interval:result.extend(interval)
        return sorted({round(max(0.,min(1.,t)),12) for t in result})


def merge_intervals(intervals):
    out=[]
    for lo,hi in sorted(intervals):
        if out and lo<=out[-1][1]+1e-12:out[-1][1]=max(hi,out[-1][1])
        else:out.append([lo,hi])
    return out


def clip_vertical_triangle(triangle,masks):
    """Clip a vertical triangle in its own (edge parameter,Y) plane."""
    pairs=[(math.dist([p[0],p[2]],[q[0],q[2]]),p,q) for p in triangle for q in triangle]
    length,p,q=max(pairs,key=lambda r:r[0])
    if length<=1e-10:return dict(unchanged=True,triangles_xyz_m=[triangle])
    start,end=[p[0],p[2]],[q[0],q[2]];dx,dz=end[0]-start[0],end[1]-start[1]
    intervals=merge_intervals([t for m in masks if(t:=a.segment_mask_interval(start,end,m))])
    if not intervals:return dict(unchanged=True,triangles_xyz_m=[triangle])
    poly=[[(dx*(v[0]-start[0])+dz*(v[2]-start[1]))/length**2,v[1]] for v in triangle]
    if a.geo.polygon_area(poly)<=a.MIN_AREA_M2:return dict(unchanged=True,triangles_xyz_m=[triangle])
    ymin=min(v[1] for v in triangle)-1;ymax=max(v[1] for v in triangle)+1
    cuts=[[[lo,ymin],[hi,ymin],[hi,ymax],[lo,ymax]] for lo,hi in intervals]
    parts=a.subtract([poly],cuts);out=[];sign=a.geo.signed_polygon_area(poly)
    for part in parts:
        if a.geo.signed_polygon_area(part)*sign<0:part=list(reversed(part))
        vv=[[start[0]+t*dx,y,start[1]+t*dz] for t,y in part]
        out.extend([vv[0],vv[i],vv[i+1]] for i in range(1,len(vv)-1))
    return dict(unchanged=False,triangles_xyz_m=out,removed_parameter_intervals=intervals)


def apply_edits(scene,patch):
    """Pure application. Native instance/asset assembly remains parent-owned."""
    original=scene['surfaces'];out=dict(scene);surfaces=dict(original);by_material={}
    for row in patch['surface_edits']:
        material,index=row['material'],row['triangle_index']
        if material not in original or not isinstance(index,int) or not 0<=index<len(original[material])//3:raise ValueError('Invalid frozen source index')
        entries=by_material.setdefault(material,{})
        if index in entries:raise ValueError('Overlapping frozen source edit; geometric composition is required')
        entries[index]=row
    ledger=[]
    for material,edits in by_material.items():
        vertices=original[material]
        if canonical_sha(vertices)!=patch['source_surface_hashes'][material]:raise ValueError('Changed source surface '+material)
        new=[];unchanged=[];ranges=[];run=None
        for start in range(0,len(vertices),3):
            index=start//3;tri=vertices[start:start+3]
            if index in edits:
                if run:ranges.append(run);run=None
                row=edits[index]
                if canonical_sha(tri)!=row['source_triangle_sha256']:raise ValueError('Changed source triangle')
                new.extend(v for t in row['replacement_triangles_xyz_m'] for v in t)
            else:
                dest=len(new)//3;new.extend(tri);unchanged.append(tri)
                if run and run['source_start']+run['count']==index and run['output_start']+run['count']==dest:run['count']+=1
                else:
                    if run:ranges.append(run)
                    run=dict(source_start=index,output_start=dest,count=1)
        if run:ranges.append(run)
        # Every unedited record is carried forward with original numeric objects.
        for run in ranges:
            src=vertices[run['source_start']*3:(run['source_start']+run['count'])*3]
            dst=new[run['output_start']*3:(run['output_start']+run['count'])*3]
            if src!=dst or any(p is not q for p,q in zip(src,dst)):raise AssertionError('Untouched triangle changed')
        surfaces[material]=new
        ledger.append(dict(material=material,unchanged_triangle_count=len(unchanged),
                           unchanged_sequence_sha256=canonical_sha(unchanged),unchanged_ranges=ranges))
    for material,vertices in patch['appended_surfaces'].items():surfaces[material]=surfaces.get(material,[])+vertices
    out['surfaces']=surfaces
    removed=set(patch.get('removed_foundation_proxy_ids',[]))
    found={r['id'] for r in scene['boxes'] if r['id'] in removed}
    if found!=removed:raise ValueError('Foundation removal ledger does not match frozen scene')
    out['boxes']=[r for r in scene['boxes'] if r['id'] not in removed]
    out['local_terrain_patch']=dict(patch_id=patch['id'],base_scene_sha256=SCENE_SHA256,
                                  unchanged_triangle_ledger=ledger,activation_status=patch['status'])
    return out
