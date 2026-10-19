"""Source-bound walking-floor profiles for authored XZ routes.

This is an offline reusable producer, not an NPC/cart controller. Callers must
nominate traversable owners and a source/observation-backed floor band. Roofs,
water and unrelated upper storeys are never inferred to be walking surfaces.
All returned heights retain exact triangle identity. Missing/ambiguous layers
and invalid support-ray intervals fail explicitly, with no height fallback.
"""
from dataclasses import dataclass
from collections import defaultdict
import math
import numpy as np

class ProfileError(ValueError):
    def __init__(self,code,details):
        self.code=code;self.details=details
        super().__init__(code+': '+str(details))

@dataclass
class Hit:
    owner: str
    face: int
    y: float
    normal_y: float
    source_sha256: str
    def record(self):
        return {'owner_id':self.owner,'source_face_index':self.face,'y_m':self.y,
                'normal_y':self.normal_y,'source_mesh_sha256':self.source_sha256}

class OwnerSurface:
    def __init__(self,owner,triangles,source_sha256,cell=5.):
        self.owner=owner;self.sha=source_sha256;self.t=np.asarray(triangles,dtype=float)
        self.cell=cell;self.grid=defaultdict(list)
        # Input uses exact Godot clockwise front faces. A downward mathematical
        # cross product is an upward ray-collidable front face in this contract.
        n=-np.cross(self.t[:,1]-self.t[:,0],self.t[:,2]-self.t[:,0]);norm=np.linalg.norm(n,axis=1)
        self.ny=np.divide(n[:,1],norm,out=np.zeros_like(norm),where=norm>0)
        for i,t in enumerate(self.t):
            if self.ny[i]<math.cos(math.radians(30)):continue
            lo=np.floor(t[:,[0,2]].min(axis=0)/cell).astype(int);hi=np.floor(t[:,[0,2]].max(axis=0)/cell).astype(int)
            for x in range(lo[0],hi[0]+1):
                for z in range(lo[1],hi[1]+1):self.grid[x,z].append(i)
    def hits(self,x,z):
        out=[]
        for i in self.grid.get((math.floor(x/self.cell),math.floor(z/self.cell)),[]):
            a,b,c=self.t[i];den=(b[0]-a[0])*(c[2]-a[2])-(c[0]-a[0])*(b[2]-a[2])
            if abs(den)<1e-14:continue
            u=((x-a[0])*(c[2]-a[2])-(c[0]-a[0])*(z-a[2]))/den
            v=((b[0]-a[0])*(z-a[2])-(x-a[0])*(b[2]-a[2]))/den
            if min(u,v,1-u-v)<-1e-8:continue
            out.append(Hit(self.owner,i,float(a[1]+u*(b[1]-a[1])+v*(c[1]-a[1])),float(self.ny[i]),self.sha))
        return out

class RouteSupportSampler:
    def __init__(self,surfaces,coincident_tolerance_m=.002):
        self.surfaces={s.owner:s for s in surfaces};self.tol=coincident_tolerance_m
    def select(self,x,z,owner_ids,expected_y,band_m=.15,authoritative_owner_ids=()):
        """Top eligible face within a documented floor stratum, never a roof search.
        Authoritative contracts take priority only when caller explicitly names
        them. Two authoritative layers at different heights are an error.
        """
        missing=set(owner_ids)-self.surfaces.keys()
        if missing:raise ProfileError('UNKNOWN_OWNER',sorted(missing))
        all_hits=[h for owner in owner_ids for h in self.surfaces[owner].hits(x,z)]
        hits=[h for h in all_hits if abs(h.y-expected_y)<=band_m]
        if not hits:raise ProfileError('OWNED_WALKING_SURFACE_MISSING',{'xz':[x,z],'expected_y':expected_y,'owners':list(owner_ids),'all_hits':[h.record()for h in all_hits]})
        authoritative=[h for h in hits if h.owner in authoritative_owner_ids]
        eligible=authoritative or hits
        levels=sorted(h.y for h in eligible)
        if levels[-1]-levels[0]>self.tol:
            raise ProfileError('AMBIGUOUS_WALKING_LAYERS',{'xz':[x,z],'hits':[h.record()for h in eligible]})
        top=max(eligible,key=lambda h:h.y)
        return top,{'coincident_faces':[h.record()for h in eligible],
                    'explicitly_subordinate_faces':[h.record()for h in hits if h not in eligible],
                    'floor_band_center_m':expected_y,'floor_band_half_range_m':band_m}

def guard_support_ray(hint_y,expected_hit,observed_hit_y=None,observed_owner=None,
                      above_m=.75,below_m=1.5,match_tolerance_m=.002):
    """Fail closed before or after a bounded support query. No ray extension."""
    start=hint_y+above_m;end=hint_y-below_m;y=expected_hit.y
    if start<=y:raise ProfileError('RAY_START_NOT_ABOVE_EXPECTED_SURFACE',{'start_y':start,'surface_y':y,'owner':expected_hit.owner})
    if end>y:raise ProfileError('EXPECTED_SURFACE_OUTSIDE_RAY_RANGE',{'end_y':end,'surface_y':y})
    if observed_hit_y is not None:
        if observed_hit_y<y-match_tolerance_m:raise ProfileError('LOWER_NATIVE_LAYER_SELECTED',{'hit_y':observed_hit_y,'expected_y':y,'hit_owner':observed_owner,'expected_owner':expected_hit.owner})
        if observed_hit_y>y+match_tolerance_m:raise ProfileError('UNEXPECTED_UPPER_LAYER_SELECTED',{'hit_y':observed_hit_y,'expected_y':y,'hit_owner':observed_owner,'expected_owner':expected_hit.owner})
    return {'start_y_m':start,'end_y_m':end,'expected_surface_y_m':y,'clearance_above_surface_m':start-y}

def project_observations(points,observations):
    q=np.asarray(points);v=np.diff(q,axis=0);ll=np.linalg.norm(v[:,[0,2]],axis=1);ss=np.r_[0,np.cumsum(ll)];rows=[]
    for o in observations:
        if o.get('ground_y_m') is None:continue
        p=np.asarray(o['capsule_center']);t=np.clip(np.sum((p[[0,2]]-q[:-1,[0,2]])*v[:,[0,2]],axis=1)/np.maximum(ll*ll,1e-20),0,1)
        proj=q[:-1]+t[:,None]*v;j=np.argmin(np.linalg.norm(proj[:,[0,2]]-p[[0,2]],axis=1))
        rows.append(dict(station=float(ss[j]+t[j]*ll[j]),ground_y=o['ground_y_m'],owner=o['support_id'],frame=o['frame'],projection_error=float(np.linalg.norm(proj[j,[0,2]]-p[[0,2]]))))
    rows.sort(key=lambda o:o['station'])
    if not rows:raise ProfileError('NO_OBSERVATIONS',{})
    return ss,rows

def generate_waypoint_profile(points,observations,sampler,contract_ids=(),band_m=.15):
    ss,obs=project_observations(points,observations);stations=np.array([o['station']for o in obs]);ys=np.array([o['ground_y']for o in obs]);profile=[];ledger=[]
    for i,(p,st) in enumerate(zip(points,ss)):
        expected=float(np.interp(st,stations,ys));nearest=min(obs,key=lambda o:abs(o['station']-st))
        owners=[nearest['owner']]+[x for x in contract_ids if x!=nearest['owner']]
        h,proof=sampler.select(p[0],p[2],owners,expected,band_m,contract_ids)
        q=[p[0],h.y,p[2]];guard=guard_support_ray(q[1],h)
        profile.append(q);ledger.append({'index':i,'station_xz_m':float(st),'original_xyz_hint_m':p,'generated_xyz_m':q,'delta_y_m':h.y-p[1],'surface':h.record(),'ownership':proof,'nearest_original_runtime_observation':nearest,'bounded_ray_guard':guard})
    return profile,ledger
