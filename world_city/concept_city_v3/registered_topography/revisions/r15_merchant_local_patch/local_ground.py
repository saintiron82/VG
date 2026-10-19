"""Finite new platform and retired-owner restoration meshes, never city resampling."""
import json,math
from collections import defaultdict
from . import author as a, frozen as f

MATERIALS={'cobblestone':'ground_stone','cultivated_soil':'ground_grass',
           'compacted_gravel':'ground','packed_earth':'ground_earth'}

class PatchQuery:
    def __init__(self,masks):
        self.masks=masks;self.index=a.geo._SpatialIndex(8)
        for i,p in enumerate(masks):self.index.add(i,p)
    def inside(self,p):
        return any(a.geo.point_in_convex_polygon(p,self.masks[i],1e-9) for i in self.index.candidates([p]))

class LocalReference:
    def __init__(self):
        raw=(a.HERE/'frozen_local_reference.json').read_bytes()
        if a.sha(a.HERE/'frozen_local_reference.json')!='496708dd84b6852475362e8088e68fb41f1cc2fc06257b76390f96878ea9a3c3':raise ValueError('Changed frozen local reference')
        data=json.loads(raw);self.records=data['local_triangles'];self.index=a.geo._SpatialIndex(8)
        for i,r in enumerate(self.records):self.index.add(i,r['polygon_xz_m'])
    def at(self,p):
        return [self.records[i] for i in sorted(self.index.candidates([p])) if a.geo.point_in_convex_polygon(p,self.records[i]['polygon_xz_m'],1e-8)]
    def edge_knots(self,p,q):
        ts=[0.,1.]
        for i in self.index.candidates([p,q]):
            span=a.segment_mask_interval(p,q,self.records[i]['polygon_xz_m'])
            if span:ts.extend(span)
        return ts


def point(p,q,t):return [(1-t)*p[k]+t*q[k] for k in (0,1)]
def fan(vertices):
    for i in range(1,len(vertices)-1):
        t=[vertices[0],vertices[i],vertices[i+1]]
        if a.geo.polygon_area([[v[0],v[2]] for v in t])>a.MIN_AREA_M2:yield t

def plane_y(row,p):return a.plane_height(row['plane_y_xz_m'],*p)


def build_ground(profile_masks=()):
    """Source candidate meshes. Public profiles are supplied separately."""
    reference=LocalReference();cut=list(profile_masks);result=[];boundary_issues=[]
    # Existing source materials already partition native holes from open ground.
    for prop in a.HANDOFF['properties']:
        y=prop['finished_floor_y_m']
        for material in prop['materials']:
            if material['material']=='native_asset_owned':continue
            for poly in material['polygons_xz_m']:
                for p in a.subtract([a.polygon(poly)],cut):
                    for tri in fan([[x,y,z] for x,z in p]):
                        result.append(dict(id=prop['property_id']+':GROUND:'+str(len(result)),
                            kind='merchant_platform',property_id=prop['property_id'],
                            material=MATERIALS[material['material']],vertices_xyz_m=tri))
    restoration=[]
    for row in a.restoration_domains():
        for p in a.subtract([row['polygon_xz_m']],cut):restoration.append(dict(row,polygon_xz_m=p))
    all_masks=[r['polygon_xz_m'] for r in a.patch_masks()]+cut;patch=PatchQuery(all_masks)
    # Add all existing restoration vertices to common edge subdivision.
    vertex_index=a.geo._SpatialIndex(4);vertices=[]
    for row in restoration:
        for p in row['polygon_xz_m']:
            vertex_index.add(len(vertices),[p]);vertices.append(p)
    prepared=[];fixed_constraints=[]
    for row in restoration:
        poly=row['polygon_xz_m'];nodes=[];node_kinds=[]
        for p,q in zip(poly,poly[1:]+poly[:1]):
            length=math.dist(p,q)
            if length<1e-9:continue
            ts=[0.,1.]+reference.edge_knots(p,q)
            # Two-metre source samples only inside these finite old domains.
            ts.extend(i/max(1,math.ceil(length/2)) for i in range(1,max(1,math.ceil(length/2))))
            for i in vertex_index.candidates([p,q]):
                dist,t=a.base.R04.base._project(*vertices[i],p,q)
                if dist<1e-8 and 0<t<1:ts.append(t)
            ts=sorted(set(round(max(0.,min(1.,t)),12) for t in ts))
            for lo,hi in zip(ts,ts[1:]):
                u,v=point(p,q,lo),point(p,q,hi);mid=point(u,v,.5)
                normal=[-(q[1]-p[1])/length*1e-5,(q[0]-p[0])/length*1e-5]
                outside=[point(mid, [mid[0]+s*normal[0],mid[1]+s*normal[1]],1) for s in (-1,1)]
                outside=[v for v in outside if not patch.inside(v)]
                frozen_rows=reference.at(outside[0]) if outside else []
                if outside and not frozen_rows:
                    boundary_issues.append(dict(id=row['id'],edge=[u,v],issue='No outside R5 top triangle; native-mask or existing omission needs explicit review.'))
                if frozen_rows:
                    selected=frozen_rows[0];h=plane_y(selected,u);kind='frozen_boundary'
                    fixed_constraints.extend([(u,h),(v,plane_y(selected,v))])
                else:
                    selected=None;h=a.base.source_surface_height_at(row['underlying_record'],*u);kind='underlying_source'
                nodes.append([u[0],h,u[1]]);node_kinds.append(kind)
        # Preserve shared XZ knots; duplicate coincident endpoints are removed.
        cleaned=[]
        for v in nodes:
            if not cleaned or math.dist([v[0],v[2]],[cleaned[-1][0],cleaned[-1][2]])>1e-9:cleaned.append(v)
        if len(cleaned)<3:continue
        prepared.append((row,cleaned))
    # Both endpoints of every external frozen segment constrain all incident
    # restoration pieces. Only fixing outgoing edges creates false corner ramps.
    fixed_index=a.geo._SpatialIndex(1)
    for i,(p,y) in enumerate(fixed_constraints):fixed_index.add(i,[p])
    for row,cleaned in prepared:
        poly=row['polygon_xz_m']
        for node in cleaned:
            p=[node[0],node[2]];ys=[fixed_constraints[i][1] for i in fixed_index.candidates([p]) if math.dist(p,fixed_constraints[i][0])<1e-8]
            if ys:
                if max(ys)-min(ys)>1e-7:boundary_issues.append(dict(id=row['id'],point_xz_m=p,issue='Incompatible inherited exterior heights',heights_m=ys))
                node[1]=ys[0]
        c=[sum(p[0] for p in poly)/len(poly),sum(p[1] for p in poly)/len(poly)]
        y=a.base.source_surface_height_at(row['underlying_record'],*c)
        # A one-variable convex minimax choice removes fan-center artifacts.
        from scipy.optimize import minimize_scalar
        pairs=[(u,v) for u,v in zip(cleaned,cleaned[1:]+cleaned[:1]) if a.geo.polygon_area([c,[u[0],u[2]],[v[0],v[2]]])>a.MIN_AREA_M2]
        def maximum_grade(h):return max(math.hypot(*a.affine_plane([[c[0],h,c[1]],u,v])[:2]) for u,v in pairs)
        if pairs and maximum_grade(y)>.120000001:
            hs=[v[1] for v in cleaned];opt=minimize_scalar(maximum_grade,bounds=(min(hs)-1,max(hs)+1),method='bounded',options={'xatol':1e-13});y=float(opt.x)
        center=[c[0],y,c[1]]
        material='alley' if row['underlying_record']['kind'] in ('door_landing','door_approach') else 'ground'
        for u,v in zip(cleaned,cleaned[1:]+cleaned[:1]):
            tri=[center,u,v]
            if a.geo.polygon_area([[p[0],p[2]] for p in tri])<=a.MIN_AREA_M2:continue
            result.append(dict(id=row['id']+':'+str(len(result)),kind='retired_owner_restoration',
                material=material,vertices_xyz_m=tri,restoration_id=row['id'],
                underlying_kind=row['underlying_record']['kind']))
    return dict(triangles=result,boundary_issues=boundary_issues,
                source_scene_sha256=f.SCENE_SHA256,profile_masks_count=len(cut))

if __name__=='__main__':
    path=a.HERE/'ground_preprofile_candidate_r2.json'
    if path.exists():raise SystemExit('Candidate evidence already exists')
    d=build_ground([r['polygon_xz_m'] for r in a.GATES]);path.write_text(json.dumps(d,separators=(',',':'))+'\n')
    count=defaultdict(int);maximum=defaultdict(float)
    for r in d['triangles']:
        count[r['kind']]+=1;g=math.hypot(*a.affine_plane(r['vertices_xyz_m'])[:2]);maximum[r['kind']]=max(maximum[r['kind']],g)
    print(dict(triangle_counts=dict(count),maximum_gradients=dict(maximum),boundary_issue_count=len(d['boundary_issues']),sha256=a.sha(path)),flush=True)
