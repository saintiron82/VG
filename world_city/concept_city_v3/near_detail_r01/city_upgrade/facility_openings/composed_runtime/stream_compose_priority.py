"""Ordered finite-ROI ownership for adjacent or overlapping interface revisions.

The frozen r04 compositor remains reproducible. A later interface evaluates the
same canonical source on both sides of its boundary, so its closed AABB owns
that face domain too. Earlier boundary adapters must not survive underneath it.
No vertex is moved and no source operation or compiled ROI is changed.
"""
from pathlib import Path
import stream_compose as base

a=base.a
sr=base.sr
Clipper=base.Clipper

class Composition(base.Composition):
    def __init__(self,catalog_path,interface_path=None):
        super().__init__(catalog_path,interface_path)
        self.extra=[]
        for record in self.item['windows']:
            source=a.load(a.ROOT/record['path'])
            for group in source['groups']:
                for quad in group['quads']:
                    self.extra.extend((group['material'],part) for part in self.interface_clip.pieces(quad))
        self.interface_priority_edits=[]
        for index,record in enumerate(self.interface_outputs):
            later=Clipper([item['region'] for item in self.interface_outputs[index+1:]])
            source=a.load(a.ROOT/record['path']);input_count=output_count=changed=0
            for group in source['groups']:
                for quad in group['quads']:
                    input_count+=1;parts=later.pieces(quad);changed+=parts!=[quad];output_count+=len(parts)
                    self.extra.extend((group['material'],part) for part in parts)
            if changed:
                self.interface_priority_edits.append({'input_path':record['path'],'input_sha256':record['sha256'],'input_quads':input_count,'output_quads':output_count,'changed_quads':changed,'later_ownership_regions':[item['region'] for item in self.interface_outputs[index+1:]],'source_shape_changed':False})
        self.bind(Path(__file__),'ordered closed-AABB interface face-domain ownership',load=False)

def selftests():
    # Same-plane old seam is removed exactly where a later region touches it;
    # the two unchanged side fragments retain their numerical coordinates.
    quad=a.rect_quad([-2,-1,2,1],1,[0,2],3,1)
    later=Clipper([{'min':[-1,3,-1],'max':[1,4,1]}])
    pieces=later.pieces(quad)
    assert len(pieces)==2
    assert sum(a.rect_area(a.quad_info(q)[4]) for q in pieces)==4
    untouched=a.rect_quad([-2,-1,2,1],1,[0,2],2.95,1)
    assert later.pieces(untouched)==[untouched]
    # The reverse-facing boundary follows the same domain ownership.
    assert sum(a.rect_area(a.quad_info(q)[4]) for q in later.pieces(list(reversed(quad))))==4
    return {'exact_touching_boundary_priority':True,'outside_plane_unchanged':True,'both_normal_directions':True}

if __name__=='__main__':
    print(selftests())
