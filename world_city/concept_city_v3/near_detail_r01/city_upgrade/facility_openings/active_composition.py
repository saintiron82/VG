"""Outside occupancy for finite patches in an active roof/window composition."""
import math

class OutsideOccupancy:
    def __init__(self,fine,coarse,active_fine_regions,roof_materials):
        self.fine={tuple(r[:3]):r for r in fine['cells']};self.coarse={tuple(r[:3]):r for r in coarse['cells']};self.regions=active_fine_regions;self.roof_materials=set(roof_materials)
    def sample(self,point):
        f=self.fine.get(tuple(math.floor(v/.05+1e-8) for v in point));o=self.coarse.get(tuple(math.floor(v/.5+1e-8) for v in point))
        if any(all(r['min'][j]<=point[j]<r['max'][j] for j in range(3)) for r in self.regions):return bool(f),f[5] if f else None,None
        if f and f[5] in self.roof_materials:return True,f[5],None
        if o and o[5] not in self.roof_materials:return True,o[5],None
        return False,None,None
