"""Bounded sparse ray occupancy of the exact retained render, streamed once.

Only requested tangent rows are indexed. Each row stores face-domain intervals,
not a dense image or solid voxel volume. Ray columns are checked on demand.
"""
import bisect,collections,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent.parent),str(HERE.parent.parent/'composed_runtime')]
import author as a
import stream_render as sr

class SparseRayCache:
    def __init__(self,path,regions,axis=0,pitch=.05,origin=(0,0,0),factory=None):
        self.pitch=pitch;self.origin=list(origin);self.axis=axis;self.t=[j for j in range(3) if j!=axis];self.rows=collections.defaultdict(list);self.memo={};self.stats={'input_quads':0,'indexed_quads':0,'interval_references':0,'validated_columns':0,'max_column_crossings':0,'query_count':0};self.domains=collections.defaultdict(list)
        for r in regions:
            lo=[math.floor((r['min'][j]-origin[j])/pitch+1e-8)-1 for j in self.t];hi=[math.ceil((r['max'][j]-origin[j])/pitch-1e-8)+1 for j in self.t]
            for u in range(lo[0],hi[0]):self.domains[u].append((lo[1],hi[1]))
        assert len(self.domains)<4096,'ray tangent-row cap'
        self.u_min=min(self.domains);self.u_max=max(self.domains)+1
        iterator=factory() if factory else ((gi,qi,m,q) for gi,qi,m,q in sr.iter_indexed_quads(path))
        for gi,qi,m,q in iterator:
            self.stats['input_quads']+=1;ax,t,p,s,r=a.quad_info(q)
            if ax!=axis:continue
            lo=[round((r[j]-origin[t[j]])/pitch) for j in range(2)];hi=[round((r[j+2]-origin[t[j]])/pitch) for j in range(2)];plane=round((p-origin[axis])/pitch)
            assert abs(origin[axis]+plane*pitch-p)<1e-6
            record=(lo[1],hi[1],p,s,m,gi,qi);used=False
            for u in range(max(lo[0],self.u_min),min(hi[0],self.u_max)):
                if any(max(lo[1],v0)<min(hi[1],v1) for v0,v1 in self.domains.get(u,[])):
                    self.rows[u].append(record);self.stats['interval_references']+=1;used=True
            self.stats['indexed_quads']+=used
        assert self.stats['interval_references']<300000,'sparse interval cap'
    def sample(self,world):
        u,v=[math.floor((world[j]-self.origin[j])/self.pitch+1e-8) for j in self.t];assert any(v0<=v<v1 for v0,v1 in self.domains.get(u,[])),('query outside declared finite tangent projection',world)
        key=(u,v);values=self.memo.get(key)
        if values is None:
            values=sorted((p,s,m,gi,qi) for v0,v1,p,s,m,gi,qi in self.rows.get(u,[]) if v0<=v<v1)
            assert len(values)%2==0,('Open retained-render ray',self.axis,key,values)
            assert all(x[1]==(-1 if i%2==0 else 1) for i,x in enumerate(values)),('Inconsistent retained-render winding',self.axis,key,values)
            assert len({x[0] for x in values})==len(values),('Coincident retained-render ray crossings',self.axis,key)
            if len(self.memo)>=8192:self.memo.clear()
            self.memo[key]=values;self.stats['validated_columns']+=1;self.stats['max_column_crossings']=max(self.stats['max_column_crossings'],len(values))
        self.stats['query_count']+=1;pos=bisect.bisect_right([x[0] for x in values],world[self.axis])
        if not pos%2:return False,None,None
        hit=min(values[pos-1:pos+1],key=lambda x:abs(x[0]-world[self.axis]));return True,hit[2],(hit[3],hit[4])

class RevisedOutside:
    def __init__(self,fine,regions,retained):
        self.cells={tuple(r[:3]):r[5] for r in fine['cells']};self.regions=regions;self.retained=retained;self.pitch=fine['pitch'];self.origin=fine['grid_origin']
    def sample(self,point):
        if any(all(r['min'][j]<=point[j]<r['max'][j] for j in range(3)) for r in self.regions):
            cell=tuple(math.floor((point[j]-self.origin[j])/self.pitch+1e-8) for j in range(3));return cell in self.cells,self.cells.get(cell),None
        return self.retained.sample(point)
