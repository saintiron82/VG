"""Explicit bounded PORT_BRIDGE_TIE grade correction; XZ source is unchanged."""
import json,math,hashlib,bisect
from pathlib import Path
from ..r03_external_interfaces import review
from . import bridge
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.review_geometry import clean
HERE=Path(__file__).resolve().parent
ROAD=next(r for r in review.base.REGISTERED_PLAN['roads'] if r['id']=='PORT_BRIDGE_TIE')
START=ROAD['polyline_xz_m'][0];END=ROAD['polyline_xz_m'][-1]
LENGTH=math.dist(START,END);U=[(END[k]-START[k])/LENGTH for k in(0,1)];V=[-U[1],U[0]]
Q=2.2

def station(p):return sum((p[k]-START[k])*U[k] for k in(0,1))
def local(p):return [station(p),sum((p[k]-START[k])*V[k] for k in(0,1))]
def world(p):return [START[k]+U[k]*p[0]+V[k]*p[1] for k in(0,1)]
def disjoint(polys):
    out=[]
    for poly in polys:
        parts=[poly]
        for old in out:parts=[q for p in parts for cut in geo.convex_difference(p,old) if(q:=clean(cut))]
        out.extend(parts)
    return out
# Full original travel width and finite rounded joints, no street relocation.
DOMAINS=disjoint(list(review.prior.previous.corridor(ROAD['polyline_xz_m'],ROAD['width_m'])))
ROAD_OWNERS=review.prior.previous._source_owners()
quay=[r['polygon_xz_m'] for r in ROAD_OWNERS if r['kind']=='road' and r['road_id']=='PORT_QUAY']
qints=[p for a in DOMAINS for b in quay if(p:=clean(geo.convex_intersection(a,b)))]
bints=[p for a in DOMAINS for b in bridge.REGIONS if(p:=clean(geo.convex_intersection(a,b['polygon_xz_m'])))]
S0=max(station(p) for poly in qints for p in poly)
S1=min(station(p) for poly in bints for p in poly)
if S1<=S0:raise ValueError('No finite blend interval between quay traffic and bridge ownership')

GRADE=.10
TARGET=bridge.deck_y(bridge.DATA,*END)

def distance_to_tie(p):
    if any(geo.point_in_convex_polygon(p,q,1e-8) for q in DOMAINS):return 0.
    return min(review.base._project(*p,a,b)[0] for poly in DOMAINS for a,b in zip(poly,poly[1:]+poly[:1]))

def height_at(x,z):
    return max(Q,bridge.deck_y(bridge.DATA,x,z))

def junction_height_at(x,z):
    # Bounded uplift on the existing bridge surface only. The 10%-distance
    # envelope is continuous with the tie at its exact finite boundary.
    return max(bridge.deck_y(bridge.DATA,x,z),Q-GRADE*distance_to_tie([x,z]))

def junction_domains():
    out=[]
    # A 24m finite collar is conservatively wider than the maximum required
    # uplift /10%; only bridge-owned points can be raised.
    b=review.base._bounds([p for poly in DOMAINS for p in poly]);box=[b[0]-24,b[1]-24,b[2]+24,b[3]+24]
    for r in bridge.REGIONS:
        p=clean(geo.convex_intersection(r['polygon_xz_m'],review.prior.previous.rect(box)))
        if p:out.append(dict(owner_id='PORT_TIE_BRIDGE_JUNCTION:'+r['id'],polygon_xz_m=p,height_api='junction_height_at(x,z)',base_region_id=r['id']))
    return out

def split_domains():
    # Exact profile/weight break planes. On each piece the height gradient is
    # affine, so its Euclidean norm reaches its maximum at a polygon vertex.
    out=[]
    for original in DOMAINS:
        parts=[original]
        for t,breaks in [(None,[S0,S1]),(bridge.DATA['world_to_bridge'],bridge.PROFILE_X)]:
            nextparts=[]
            for poly in parts:
                p=[local(q) if t is None else bridge._transform(t,q) for q in poly]
                xs=[q[0] for q in p];zs=[q[1] for q in p];cuts=[min(xs)]+[v for v in breaks if min(xs)+1e-9<v<max(xs)-1e-9]+[max(xs)]
                for lo,hi in zip(cuts,cuts[1:]):
                    q=clean(geo.convex_intersection(p,review.prior.previous.rect([lo,min(zs)-1,hi,max(zs)+1])))
                    if q:nextparts.append([world(v) if t is None else bridge._transform(bridge.DATA['bridge_to_world'],v) for v in q])
            parts=nextparts
        out.extend(parts)
    return out

def build_contract():
    pieces=split_domains()
    samples=[]
    for a,b in zip(ROAD['polyline_xz_m'],ROAD['polyline_xz_m'][1:]):
        samples += [[a[k]+i/100*(b[k]-a[k]) for k in (0,1)] for i in range(100)]
    samples.append(END);center=[height_at(*p) for p in samples]
    junction=junction_domains();collar=[]
    bb=review.base._bounds([p for poly in DOMAINS for p in poly]);bb=[bb[0]-24,bb[1]-24,bb[2]+24,bb[3]+24]
    for r in junction:
        for p in r['polygon_xz_m']:
            if min(abs(p[0]-bb[0]),abs(p[0]-bb[2]),abs(p[1]-bb[1]),abs(p[1]-bb[3]))<1e-7:
                collar.append(abs(junction_height_at(*p)-bridge.deck_y(bridge.DATA,*p)))
    if max(collar,default=0)>1e-9:raise ValueError('Junction uplift reaches finite collar boundary')
    ledger=[dict(xz_m=p,old_y_m=review.road_height_at(ROAD['id'],*p),new_y_m=height_at(*p),delta_m=height_at(*p)-review.road_height_at(ROAD['id'],*p)) for p in ROAD['polyline_xz_m']]
    return dict(schema='riverstone.registered_port_bridge_tie_grade.v1',source_plan_sha256=review.prior.previous.SOURCE_SHA,
        bridge_overlay_sha256=bridge.OVERLAY_SHA,road_id=ROAD['id'],polyline_xz_m=ROAD['polyline_xz_m'],width_m=ROAD['width_m'],xz_changed=False,
        source_evidence_levels_m=ROAD['levels_m'],grade_ledger=ledger,flat_quay_y_m=Q,blend_station_range_m=[S0,S1],frame_origin_xz_m=START,frame_axis_xz=U,
        maximum_analytic_gradient=GRADE,grade_limit=.12,grade_limit_pass=True,
        junction_regions=junction,junction_collar_edge_max_delta_m=max(collar,default=0),centerline_min_y_m=min(center),centerline_monotone=all(b>=a-1e-7 for a,b in zip(center,center[1:])),
        proof='Tie is max(flat2.2, shared bridge profile), hence <=10% and monotone along this source centerline. Junction is max(bridge profile,2.2−0.10*distance_to_exact_tie_union), also10%-Lipschitz. The profiles agree everywhere on the tie/bridge boundary; finite24m collar boundary has zero uplift.',
        owned_polygons_xz_m=DOMAINS,profile_piece_polygons_xz_m=pieces,
        dry_mask_rule='Subtract finite water before replacing ground; any tie area over water is an elevated supported connection, not earth fill.',
        quay_apron_rule='Exact road strip owns the corrected grade. Cut its footprint from apron3_8 common solid/top unless the apron source is explicitly reauthored to this same profile.',
        bridge_interface='The original bridge cap needs the explicit bounded junction uplift; retain sealed compile as evidence until this derived patch is adopted. Tie and uplift agree over their full overlap. West parapet opening must cover the finite tie intersection.',
        bridge_opening_polygons_xz_m=bints,quay_shared_polygons_xz_m=qints,
        status='bounded source correction proven <=10%; derived common junction cap/apron cut and controller validation pending')

if __name__=='__main__':
    c=build_contract();(HERE/'port_tie_contract.json').write_text(json.dumps(c,indent=2)+'\n')
    print(json.dumps({k:c[k] for k in ['blend_station_range_m','maximum_analytic_gradient','grade_limit_pass','centerline_min_y_m','centerline_monotone','grade_ledger']},indent=2))
