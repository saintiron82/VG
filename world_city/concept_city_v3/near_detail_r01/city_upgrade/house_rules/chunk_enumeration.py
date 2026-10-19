"""Conservative chunk ownership from unchanged common paint candidate ranges.

The arithmetic exactly matches common.points_in's unbounded integer ranges.
No contains predicate is approximated: chunks with no paint candidate address
cannot own an occupied cell. Halo sampling for retained chunks is unchanged.
"""
import itertools
import math


def enumerate_paint_chunks(source,origin,edge,epsilon,max_chunks=100000):
    if type(edge)is not int or edge<1:raise ValueError('Positive integer chunk edge required')
    pitch=source.pitch;owners=set();paint_operations=0
    for instance,component,transform,operations in source.items:
        for original,prepared,placement,low,high in operations:
            if original['action']!='paint':continue
            paint_operations+=1
            lo=[math.floor((low[j]-origin[j])/pitch+epsilon) for j in range(3)]
            hi=[math.ceil((high[j]-origin[j])/pitch-epsilon) for j in range(3)]
            if any(lo[j]>=hi[j] for j in range(3)):continue
            spans=[range(lo[j]//edge,(hi[j]-1)//edge+1) for j in range(3)]
            if math.prod(map(len,spans))>max_chunks:raise ValueError('Paint AABB ownership chunk budget exceeded')
            owners.update(itertools.product(*spans))
            if len(owners)>max_chunks:raise ValueError('Paint union ownership chunk budget exceeded')
    bounds=source.bounds
    lo=[math.floor((bounds[0][j]-origin[j])/pitch+epsilon) for j in range(3)]
    hi=[math.ceil((bounds[1][j]-origin[j])/pitch-epsilon) for j in range(3)]
    dense_count=math.prod(max(0,(hi[j]-1)//edge-lo[j]//edge+1) for j in range(3))
    return {'owned_lows':[[n*edge for n in point] for point in sorted(owners)],
        'dense_bbox_chunks':dense_count,'scheduled_chunks':len(owners),'proven_empty_chunks_skipped':dense_count-len(owners),
        'paint_operations':paint_operations,'sampling_predicates_changed':False,
        'empty_chunk_proof':'No original transformed paint AABB can enumerate an owned common integer candidate address.',
        'halo_policy':'Every scheduled owned chunk still compiles its unchanged full halo; skipped ownership chunks are provably empty.'}
