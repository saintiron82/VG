"""Exact streaming six-neighbor connectivity, without a whole-building cell union.

This validates cells already sampled by unchanged common/core.py; it does not
sample geometry. Keep only local component counts and cross-chunk boundary keys.
"""
from collections import deque


class ConnectedAccumulator:
    def __init__(self,max_boundary_cells=500000):
        self.parents=[];self.sizes=[];self.boundary={};self.total=0
        self.first_point=None;self.first_node=None;self.peak_local_cells=0
        self.max_boundary_cells=max_boundary_cells

    @staticmethod
    def neighbors(p):
        for axis in range(3):
            for sign in (-1,1):
                q=list(p);q[axis]+=sign;yield tuple(q)

    def root(self,node):
        while self.parents[node]!=node:
            self.parents[node]=self.parents[self.parents[node]];node=self.parents[node]
        return node

    def join(self,left,right):
        left,right=self.root(left),self.root(right)
        if left==right:return
        if self.sizes[left]<self.sizes[right]:left,right=right,left
        self.parents[right]=left;self.sizes[left]+=self.sizes[right]

    def add_chunk(self,points,lo,hi):
        remaining=set(points);self.total+=len(remaining)
        self.peak_local_cells=max(self.peak_local_cells,len(remaining))
        if any(not all(lo[j]<=p[j]<hi[j] for j in range(3)) for p in remaining):
            raise ValueError('Connectivity point violates chunk ownership')
        while remaining:
            start=min(remaining);remaining.remove(start)
            node=len(self.parents);self.parents.append(node);self.sizes.append(0)
            if self.first_point is None or start<self.first_point:self.first_point=start;self.first_node=node
            queue=deque([start])
            while queue:
                p=queue.popleft();self.sizes[self.root(node)]+=1
                edge=any(p[j]==lo[j] or p[j]==hi[j]-1 for j in range(3))
                if edge:
                    if p in self.boundary:raise ValueError('Connectivity chunk overlap')
                    self.boundary[p]=node
                    if len(self.boundary)>self.max_boundary_cells:
                        raise ValueError('Connected constraint boundary budget exceeded; pending without fallback')
                for q in self.neighbors(p):
                    if q in remaining:remaining.remove(q);queue.append(q)
                    elif edge and q in self.boundary:self.join(node,self.boundary[q])

    def result(self):
        reached=self.sizes[self.root(self.first_node)] if self.first_node is not None else 0
        return {'pass':bool(self.total) and reached==self.total,'occupied_cells':self.total,
                'unreached_cells':self.total-reached,'connected_components':len({self.root(i) for i in range(len(self.parents))}),
                'retained_boundary_cells':len(self.boundary),'peak_local_selected_cells':self.peak_local_cells,
                'whole_building_cell_union_created':False,
                'method':'Per-owned-chunk 6-neighbor components joined only through adjacent boundary cells; common connected semantics.'}
