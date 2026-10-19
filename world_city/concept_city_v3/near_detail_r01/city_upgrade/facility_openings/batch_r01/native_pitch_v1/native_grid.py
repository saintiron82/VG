"""Opt-in native-grid coordinate and outside-ownership adapter.

No source geometry is generated, cropped or mutated. Common samplers and
existing seam meshing remain responsible for the exact source predicates.
"""
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class Grids:
    native_pitch:float=.5
    detail_pitch:float=.05
    native_origin:tuple=(0,0,0)
    detail_origin:tuple=(0,0,0)
    def __post_init__(self):
        assert all(math.isfinite(v) and v>0 for v in [self.native_pitch,self.detail_pitch])
        assert len(self.native_origin)==len(self.detail_origin)==3
        assert all(math.isfinite(v) for v in (*self.native_origin,*self.detail_origin))
        ratio=self.native_pitch/self.detail_pitch
        assert ratio>=1 and abs(ratio-round(ratio))<1e-8,'Noncommensurate pitches'
        offset=[(a-b)/self.detail_pitch for a,b in zip(self.native_origin,self.detail_origin)]
        assert all(abs(v-round(v))<1e-8 for v in offset),'Noncommensurate grid origins'
    @property
    def ratio(self):return round(self.native_pitch/self.detail_pitch)
    @property
    def offset(self):return tuple(round((a-b)/self.detail_pitch) for a,b in zip(self.native_origin,self.detail_origin))
    def world_cell(self,point,detail=False):
        origin,pitch=(self.detail_origin,self.detail_pitch) if detail else (self.native_origin,self.native_pitch)
        return tuple(math.floor((v-o)*(1/pitch)+1e-8) for v,o in zip(point,origin))
    def native_bounds(self,fine_bounds,halo=1):
        assert type(halo)is int and halo>=0
        assert all(type(v)is int for a in fine_bounds.values() for v in a)
        return {'min':[(v-o)//self.ratio-halo for v,o in zip(fine_bounds['min'],self.offset)],'max':[-(-(v-o)//self.ratio)+halo for v,o in zip(fine_bounds['max'],self.offset)]}
    def contact_domain(self,low,high):
        p=self.native_pitch
        return {'min':[o+math.floor((v-o-p)*(1/p)+1e-8)*p for v,o in zip(low,self.native_origin)],'max':[o+math.ceil((v-o+p)*(1/p)-1e-8)*p for v,o in zip(high,self.native_origin)]}

class ExactOutside:
    def __init__(self,fine,coarse,roof,regions,roof_materials,grids=None):
        self.grids=grids or Grids(coarse['pitch'],fine['pitch'],tuple(coarse['grid_origin']),tuple(fine['grid_origin']))
        assert coarse['pitch']==self.grids.native_pitch and fine['pitch']==self.grids.detail_pitch
        assert tuple(coarse['grid_origin'])==self.grids.native_origin and tuple(fine['grid_origin'])==self.grids.detail_origin
        self.fine={tuple(r[:3]):r[5] for r in fine['cells']};self.coarse={tuple(r[:3]):r[5] for r in coarse['cells']};self.roof=roof;self.regions=regions;self.roof_materials=roof_materials
    def sample(self,point):
        p=self.grids.world_cell(point,True)
        if any(all(r['min'][j]<=point[j]<r['max'][j] for j in range(3)) for r in self.regions):return p in self.fine,self.fine.get(p),None
        if p in self.roof:return True,self.roof[p],None
        mat=self.coarse.get(self.grids.world_cell(point));return bool(mat and mat not in self.roof_materials),mat,None
