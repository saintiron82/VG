"""Exact grid-interface seam adapter for an axis-aligned replacement volume.

Retain the original coarse skin outside the volume. Keep the unwarped fine
skin inside. Remove artificial fine ROI caps and emit only the XOR of original
coarse outside occupancy and fine inside occupancy on each interface plane.
This is a render mesh adapter; it does not change common primitives/colliders.
"""
from collections import Counter,defaultdict
import bisect,itertools,math
import author as a

class CacheOccupancy:
    """Exact half-open +Z ray parity from original closed voxel-cache quads."""
    def __init__(self,render):
        self.pitch=render['pitch'];self.origin=render['grid_origin'];self.columns=defaultdict(list)
        for gi,g in enumerate(render['groups']):
            for qi,q in enumerate(g['quads']):
                axis,t,plane,sign,rect=a.quad_info(q)
                for v in q:
                    assert all(abs((v[j]-self.origin[j])/self.pitch-round((v[j]-self.origin[j])/self.pitch))<1e-6 for j in range(3))
                if axis!=2:continue
                lo=[round((rect[j]-self.origin[j])/self.pitch) for j in range(2)];hi=[round((rect[j+2]-self.origin[j])/self.pitch) for j in range(2)]
                for x,y in itertools.product(range(lo[0],hi[0]),range(lo[1],hi[1])):self.columns[x,y].append((plane,g['material'],gi,qi,sign))
        for key,values in self.columns.items():
            values.sort();assert len(values)%2==0,('Open source cache Z ray',key,values)
            assert all(v[4]==(-1 if i%2==0 else 1) for i,v in enumerate(values)),('Inconsistent source cache winding',key)
            assert len({v[0] for v in values})==len(values),('Coincident source cache surfaces',key)
    def sample(self,world):
        key=tuple(math.floor((world[j]-self.origin[j])/self.pitch) for j in range(2));values=self.columns.get(key,[])
        pos=bisect.bisect_right([v[0] for v in values],world[2]);inside=bool(pos%2)
        if not inside:return False,None,None
        v=min(values[pos-1:pos+1],key=lambda v:abs(v[0]-world[2]));return True,v[1],(v[2],v[3])

def greedy_plane(mask,axis,sign,plane,pitch,origin):
    mask=set(mask);quads=[]
    while mask:
        x,y=min(mask,key=lambda t:(t[1],t[0]));w=1
        while (x+w,y) in mask:w+=1
        h=1
        while all((x+j,y+h) in mask for j in range(w)):h+=1
        mask.difference_update((x+j,y+k) for j in range(w) for k in range(h));q=[]
        for u,v in [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]:
            p=[0,0,0];p[axis]=plane;p[(axis+1)%3]=u;p[(axis+2)%3]=v;q.append([origin[j]+p[j]*pitch for j in range(3)])
        if sign<0:q.reverse()
        quads.append(q)
    return quads

def on_cap(q,lo,hi,pitch,origin):
    axis,t,plane,sign,r=a.quad_info(q);return any(abs(plane-(origin[axis]+bound[axis]*pitch))<1e-7 for bound in [lo,hi])

def interface_segments(quads,cb,pitch,origin):
    counts=Counter();lo,hi=cb['min'],cb['max']
    for q in quads:
        p=[[round((v[j]-origin[j])/pitch) for j in range(3)] for v in q]
        for first,last in zip(p,p[1:]+p[:1]):
            varying=[j for j in range(3) if first[j]!=last[j]]
            if len(varying)!=1:continue
            d=varying[0];planes=[j for j in range(3) if j!=d and first[j]==last[j] and first[j] in (lo[j],hi[j])]
            if not planes:continue
            low,high=sorted((first[d],last[d]))
            for k in range(max(low,lo[d]),min(high,hi[d])):
                start=first[:];start[d]=k;end=start[:];end[d]+=1
                if all(lo[j]<=start[j]<=hi[j] for j in range(3)):counts[tuple(start),tuple(end)]+=1
    return counts

def build(source_render,compiled,fine_preview,patch,protected_cuts=(), *, owned_bounds=None, validate_edges=True, occupancy=None):
    pitch=compiled['pitch'];origin=compiled['grid_origin'];cb=patch['fine_cell_bounds'];lo,hi=cb['min'],cb['max'];cells={tuple(r[:3]):r for r in compiled['cells']};occupancy=occupancy or CacheOccupancy(source_render);owned=owned_bounds or cb;masks=defaultdict(set);sample_counts=Counter();suppliers=set();entry_violations=0
    for axis in range(3):
        u,v=(axis+1)%3,(axis+2)%3
        for sign in [-1,1]:
            plane=lo[axis] if sign<0 else hi[axis]
            if (owned['min'][axis] if sign<0 else owned['max'][axis])!=plane:continue
            for uu,vv in itertools.product(range(owned['min'][u],owned['max'][u]),range(owned['min'][v],owned['max'][v])):
                inside=[0,0,0];inside[axis]=lo[axis] if sign<0 else hi[axis]-1;inside[u]=uu;inside[v]=vv;outside=inside[:];outside[axis]+=sign
                row=cells.get(tuple(inside));fine=bool(row);world=[origin[j]+(outside[j]+.5)*pitch for j in range(3)];old,material,supplier=occupancy.sample(world);sample_counts[f'coarse_{int(old)}_fine_{int(fine)}']+=1
                if fine==old:continue
                normal=sign if fine else -sign;material=row[5] if fine else material;masks[axis,normal,plane,material].add((uu,vv))
                if supplier:suppliers.add(supplier)
                center=world[:];center[axis]=origin[axis]+plane*pitch
                # An interface inside a protected entrance must have both sides
                # inside that entrance to count as a new obstruction. Door jamb
                # surfaces on the authored boundary are intentionally retained.
                for cut in protected_cuts:
                    shape=a.core.prepare_shape(cut['shape'],pitch);tr=a.core.transform(cut.get('transform'));p1=center[:];p2=center[:];p1[axis]-=pitch*.1;p2[axis]+=pitch*.1
                    if a.core.contains(shape,a.core.inverse(tr,p1),epsilon=1e-7) and a.core.contains(shape,a.core.inverse(tr,p2),epsilon=1e-7):entry_violations+=1
    groups=defaultdict(list)
    for (axis,sign,plane,material),mask in masks.items():groups[material]+=greedy_plane(mask,axis,sign,plane,pitch,origin)
    kept=defaultdict(list);dropped=0
    for g in fine_preview['groups']:
        for q in g['quads']:
            if on_cap(q,lo,hi,pitch,origin):dropped+=1
            else:kept[g['material']].append(q)
    fine_groups=[{'material':m,'quads':q} for m,q in sorted(kept.items())];seam_groups=[{'material':m,'quads':q} for m,q in sorted(groups.items())]
    checked=closure(source_render,patch,fine_groups,seam_groups,pitch,origin) if validate_edges else {'unit_interface_edge_count':None,'unpaired_interface_edges':None}
    seam_quads=[q for qs in groups.values() for q in qs]
    assert entry_violations==0,('Interface added a face inside an entry',patch['id'],entry_violations)
    result={'schema':'riverstone.facility_openings.seam.v1','patch_id':patch['id'],'source_cache_proof':'Closed alternating outward-wound Z-ray intervals, exact half-open coarse-grid columns.','fine_cell_bounds':cb,'fine_pitch_m':pitch,'grid_origin':origin,'fine_payload_hash':compiled['payload_hash'],'source_cache_group_quad_suppliers':[list(x) for x in sorted(suppliers)],'remove_artificial_fine_roi_caps':True,'fine_roi_cap_quads_removed':dropped,'fine_exterior_groups':[{'material':m,'quads':q} for m,q in sorted(kept.items())],'transition_groups':[{'material':m,'quads':q} for m,q in sorted(groups.items())],'interface_pixel_counts':dict(sample_counts),'transition_unit_faces':sum(len(mask) for mask in masks.values()),'transition_quads':len(seam_quads),'transition_area_m2':sum(len(mask) for mask in masks.values())*pitch*pitch,'owned_cell_bounds':owned,'unit_interface_edge_count':checked['unit_interface_edge_count'],'unpaired_interface_edges':checked['unpaired_interface_edges'],'protected_entry_interface_violations':entry_violations,'fine_shape_deformation':False,'coarse_outer_envelope_growth':False,'collider_changed':False,'runtime_activated':False}
    return result


def closure(source_render,patch,fine_groups,seam_groups,pitch,origin):
    edits=a.cache_contract(source_render,[patch]);lookup={(e['group_index'],e['quad_index']):e for e in edits};coarse=[]
    for gi,g in enumerate(source_render['groups']):
        for qi,q in enumerate(g['quads']):
            e=lookup.get((gi,qi));coarse+=e['retained_quads'] if e else [q]
    fine_quads=[q for g in fine_groups for q in g['quads']];seam_quads=[q for g in seam_groups for q in g['quads']]
    segments=interface_segments(coarse+fine_quads+seam_quads,patch['fine_cell_bounds'],pitch,origin);odd=[(k,n) for k,n in segments.items() if n%2]
    assert not odd,('Unpaired fine/coarse interface edges',patch['id'],len(odd),odd[:3])
    return {'unit_interface_edge_count':len(segments),'unpaired_interface_edges':len(odd)}
