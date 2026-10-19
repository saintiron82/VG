"""Frozen pure bookkeeping copied from R15; no terrain module import."""
import hashlib,json
SCENE_SHA256='a78e1b56bd59b06ec30d4bebec9f6da9d686dca87e6ef87f1d4da181f717a01a'
def canonical_sha(value):return hashlib.sha256(json.dumps(value,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def bounds(poly):return [min(p[0] for p in poly),min(p[1] for p in poly),max(p[0] for p in poly),max(p[1] for p in poly)]
def overlap(b,c):return b[0]<=c[2] and c[0]<=b[2] and b[1]<=c[3] and c[1]<=b[3]
def affine_plane(triangle):
 a,b,c=triangle;dx1,dz1=b[0]-a[0],b[2]-a[2];dx2,dz2=c[0]-a[0],c[2]-a[2];det=dx1*dz2-dx2*dz1
 gx=((b[1]-a[1])*dz2-(c[1]-a[1])*dz1)/det;gz=(dx1*(c[1]-a[1])-dx2*(b[1]-a[1]))/det
 return gx,gz,a[1]-gx*a[0]-gz*a[2]
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
