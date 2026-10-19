"""Keep original common polygon predicates at every relevant grid sample.

Clipping a sloped edge changes floating-point ray arithmetic at exact-edge cell
centers. If any local-XY predicate differs, retain that operation's original XY
polygon, with only its extrusion interval clipped. The unchanged common
compiler still performs every geometry sample and ordered paint/cut operation.
"""
import math


def check_polygon_samples(core,original,cropped,placement,world_lo,world_hi,origin,pitch):
    if original==cropped:return {'pass':True,'sample_count':0,'polygon_unchanged':True}
    axes=[next(i for i in range(3) if abs(placement['basis'][i][j])>.5) for j in (0,1)]
    intervals=[]
    for local,world in enumerate(axes):
        values=[placement['translation'][world]+placement['basis'][world][local]*p[local] for p in original]
        low=max(world_lo[world],min(values));high=min(world_hi[world],max(values))
        samples=[]
        for index in range(math.floor((low-origin[world])/pitch+core.EPS),math.ceil((high-origin[world])/pitch-core.EPS)):
            center=origin[world]+(index+.5)*pitch
            if low-core.EPS*pitch<=center<=high+core.EPS*pitch:
                samples.append((index,placement['basis'][world][local]*(center-placement['translation'][world])))
        intervals.append(samples)
    count=0
    for ix,x in intervals[0]:
        for iy,y in intervals[1]:
            count+=1
            if core.inside_polygon(x,y,original)!=core.inside_polygon(x,y,cropped):
                return {'pass':False,'sample_count':count,'first_mismatch_local_xy':[x,y],
                        'first_mismatch_world_axis_indices':[[axes[0],ix],[axes[1],iy]]}
    return {'pass':True,'sample_count':count,'polygon_unchanged':False}
