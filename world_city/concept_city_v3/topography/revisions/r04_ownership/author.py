"""Bounded next revision: exact source surface ownership, no compiler invocation.

The current v3 author and contract remain frozen. This module adds six explicitly
screened poor compounds and finite bed/bank source geometry for a later renderer.
"""
from __future__ import annotations
import copy,hashlib,json,math
from pathlib import Path
from ... import author as base
from ...next_stage_plan import parcel_candidates,voxel_stage_plan
from world_city.runtime_city.checks.placement import convex_intersection,convex_difference,polygon_area
HERE=Path(__file__).resolve().parent
BASE_SOURCE_SHA256='b341bdf4547dffd3a8ca8e7c2e4ed5bae8520c36bcfa13e3bea925bd9e89f89a'
BASE_CONTRACT_SHA256='78c7ba12d03177e27010194c17ac65a4842caf8c0d3ac89b99d6e0dca6c99062'
ACCEPTED_POOR_IDS={'P_COURT_008','P_COURT_009','P_COURT_010','P_COURT_016','P_COURT_017','P_COURT_018'}
_CANDIDATES=None


def _snapshot_check():
    if base.SOURCE_PLAN_SHA256!=BASE_SOURCE_SHA256:raise ValueError('Frozen source snapshot changed')
    if hashlib.sha256((base.HERE/'contract.json').read_bytes()).hexdigest()!=BASE_CONTRACT_SHA256:
        raise ValueError('Frozen base terrain contract changed')


def compound_candidates():
    global _CANDIDATES
    if _CANDIDATES is not None:return _CANDIDATES
    _snapshot_check();_CANDIDATES=parcel_candidates()['candidates']
    plots={p['id']:p for p in base.SOURCE_PLAN['plots']}
    for p in _CANDIDATES:
        plot=plots[p['plot_id']];p['gate_xz_m']=plot['gate_position_xz_m'];p['id']=p['plot_id']+':COMPOUND_PAD_R04'
        if p['plot_id'] in ACCEPTED_POOR_IDS:
            if p['rejection_reasons'] or p['road_overlap_area_sum_m2']>1e-7 or p['water_overlap_area_m2']>1e-7:
                raise ValueError('Accepted plot no longer meets finite source checks: '+p['plot_id'])
            p['status']='accepted_bounded_source_geometry_not_physics_or_engineering_approval'
            p['shoulder_ownership']='exact whole property plot is a declared hole in public shoulders; actual road surfaces are untouched'
            p['gate_path_contract']='flat full-width primary gate; source path beyond plot returns the shared street grade'
            p['geometry_status']='source pad/retaining domains; common solids not compiled'
        elif plot['property_type']=='merchant_court':
            # The frozen property recipe needs shop frontages as well as its main drive.
            o=plot['origin_xz_m'];yaw=plot['yaw_rad'];z=plot['depth_m']/2
            for x in [-10,10]:
                q=[o[0]+x*math.cos(yaw)+z*math.sin(yaw),o[1]-x*math.sin(yaw)+z*math.cos(yaw)]
                p['gate_ledger'].append(dict(id='shop_w' if x<0 else 'shop_e',xz_m=q,
                    threshold_y_m=p['floor_y_m'],landing_y_m=base.road_height_at(plot['road_id'],*q),
                    delta_m=p['floor_y_m']-base.road_height_at(plot['road_id'],*q),
                    status='rejected_level_frontage_needs_replan'))
    return _CANDIDATES


def compound_pads():
    return base.compound_pads()+[p for p in compound_candidates() if p['plot_id'] in ACCEPTED_POOR_IDS]


def building_pads():
    """Keep body ledgers consistent with the newly owned whole-compound datum."""
    pads=copy.deepcopy(base.building_pads());hosts={p['plot_id']:p for p in compound_pads()}
    for pad in pads:
        host=hosts.get(pad.get('plot_id'))
        if not host:continue
        floor=host['floor_y_m'];pad['floor_y_m']=floor
        natural=[base.dry_height_at(*q) for q in pad['body_polygon_xz_m']]
        pad['foundation_bottom_y_m']=min(floor,*natural)-.4
        pad['maximum_cut_m']=max(0,max(natural)-floor);pad['maximum_fill_m']=max(0,floor-min(natural))
        for entry in pad['entrance_ledger']:
            entry.update(threshold_y_m=floor,landing_y_m=floor,delta_m=0,
                routing_status='compound_floor_owned',minimum_centerline_ramp_grade=0,
                collision_status='internal proxy door at compound datum; actual asset local threshold pending')
    return pads


def land_height_at(x,z):
    for p in compound_candidates():
        if p['plot_id'] in ACCEPTED_POOR_IDS and base._inside(x,z,p['source_plot_polygon_xz_m']):return p['floor_y_m']
    return base.land_height_at(x,z)


def height_at(x,z):
    water=base.water_samples_at(x,z)
    if water:return min(base.dry_height_at(x,z),*(w['bed_y_m'] for w in water))
    return land_height_at(x,z)


def road_height_at(road_id,x,z):return base.road_height_at(road_id,x,z)


def path_height_at(path_id,x,z):
    for p in compound_candidates():
        if p['plot_id'] in ACCEPTED_POOR_IDS and base._inside(x,z,p['source_plot_polygon_xz_m']):return p['floor_y_m']
    return base.path_height_at(path_id,x,z)


def water_height_at(surface_id,x,z,segment_index=0):return base.water_height_at(surface_id,x,z,segment_index)
def finite_water_polygons():return base.finite_water_polygons()
def river_water_y(x):return base.river_water_y(x)


_OWNERS=None;_OWNER_INDEX=None

def _source_owners():
    """A spatially indexed list of analytic/source polygons, not a new mesher."""
    global _OWNERS,_OWNER_INDEX
    if _OWNERS is not None:return _OWNERS
    _OWNERS=[];_OWNER_INDEX={}
    def add(owner,kind,poly,priority,**kw):
        if len(poly)<3 or polygon_area(poly)<1e-8:return
        _OWNERS.append(dict(owner_id=owner,kind=kind,polygon_xz_m=poly,priority=priority,**kw))
    for w in finite_water_polygons():add(w['surface_id'],'water_hole',w['polygon_xz_m'],0,**{k:v for k,v in w.items() if k not in ['polygon_xz_m']})
    for road in base.SOURCE_PLAN['roads']:
        for a,b in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):
            add(road['id'],'road',base._strip(a,b,road['width_m']),10,height_api='road_height_at')
            add(road['id']+':SHOULDER','road_shoulder',base._strip(a,b,road['width_m']+4),60,height_api='road_height_at',road_id=road['id'])
    compounds={p['plot_id']:p for p in compound_pads()}
    for pad in base.building_pads():
        host=compounds.get(pad.get('plot_id'));floor=host['floor_y_m'] if host else pad['floor_y_m']
        add(pad['building_id'],'building_foundation_hole',pad['body_polygon_xz_m'],20,floor_y_m=floor)
    for pad in compound_pads():
        # Exterior noble aprons are separate transition proposals; exact whole plots own the slabs.
        add(pad['plot_id'],'compound',pad['source_plot_polygon_xz_m'],30,floor_y_m=pad['floor_y_m'])
    for stair in base.actual_stairs():
        for i,t in enumerate(stair.get('treads',[])):
            add(stair['id']+':TREAD:'+str(i),'stair_tread',t['polygon_xz_m'],40,floor_y_m=t['top_y_m'])
    for path in base.SOURCE_PLAN['paths']:
        for a,b in zip(path['polyline_xz_m'],path['polyline_xz_m'][1:]):
            add(path['id'],'path',base._strip(a,b,path['width_m']),50,height_api='path_height_at')
    for terrace in base._terrace_data():
        add(terrace['id'],'terrace',terrace['polygon_xz_m'],70,floor_y_m=terrace['top_y_m'],
            exclusion_polygons_xz_m=[p['polygon_xz_m'] for p in terrace['exclusions']])
    _OWNERS.sort(key=lambda p:(p['priority'],p['owner_id']))
    for i,p in enumerate(_OWNERS):
        r=base._bounds(p['polygon_xz_m'])
        for ix in range(math.floor(r[0]/32),math.floor(r[2]/32)+1):
            for iz in range(math.floor(r[1]/32),math.floor(r[3]/32)+1):_OWNER_INDEX.setdefault((ix,iz),[]).append(i)
    return _OWNERS


def surface_domains(bounds_xz_m):
    """Disjoint finite analytic owners for one <=32 m tile, including holes.

    Each polygon is clipped exactly before any renderer samples its owner's H.
    One shared vertex may have two levels only at an explicitly retained riser.
    """
    x0,z0,x1,z1=bounds_xz_m
    if not (0<x1-x0<=32 and 0<z1-z0<=32):raise ValueError('Bounded ownership query must be <=32 m per side')
    tile=base._rect_poly(bounds_xz_m);owners=_source_owners();ids=set()
    for ix in range(math.floor(x0/32),math.floor(x1/32)+1):
        for iz in range(math.floor(z0/32),math.floor(z1/32)+1):ids.update(_OWNER_INDEX.get((ix,iz),[]))
    remaining=[tile];out=[]
    for i in sorted(ids):
        owner=owners[i]
        if not base._overlap(bounds_xz_m,base._bounds(owner['polygon_xz_m'])):continue
        masks=[convex_intersection(tile,owner['polygon_xz_m'])]
        for hole in owner.get('exclusion_polygons_xz_m',[]):
            if not base._overlap(bounds_xz_m,base._bounds(hole)):continue
            masks=[q for p in masks for q in convex_difference(p,hole) if polygon_area(q)>1e-8]
        for mask in masks:
            if polygon_area(mask)<1e-8:continue
            new=[]
            for p in remaining:
                if not base._overlap(base._bounds(p),base._bounds(mask)):new.append(p);continue
                intersection=convex_intersection(p,mask)
                if polygon_area(intersection)>1e-8:
                    record={k:v for k,v in owner.items() if k not in ['polygon_xz_m','exclusion_polygons_xz_m']}
                    record['polygon_xz_m']=intersection;out.append(record)
                new.extend(q for q in convex_difference(p,mask) if polygon_area(q)>1e-8)
            remaining=new
    out.extend(dict(owner_id='BASE_GROUND',kind='ground',polygon_xz_m=p,priority=100,height_api='dry_height_at') for p in remaining)
    return out


def surface_height_at(record,x,z):
    if 'floor_y_m' in record:return record['floor_y_m']
    kind=record['kind']
    if kind=='water_hole':return water_height_at(record['surface_id'],x,z,record.get('segment_index',0))
    if kind in ['road','road_shoulder']:return road_height_at(record.get('road_id',record['owner_id']),x,z)
    if kind=='path':return path_height_at(record['owner_id'],x,z)
    return base.dry_height_at(x,z)


def channel_support_domains(surface_id='SPRING_FEEDER'):
    """Exact finite bed polygons plus exterior bank faces; internal joins removed."""
    domains=finite_water_polygons();selected=[d for d in domains if d['surface_id']==surface_id]
    depth=next(w['bed_depth_m'] for w in base.WATER_SURFACES if w['id']==surface_id)
    beds=[];banks=[]
    for domain in selected:
        poly=domain['polygon_xz_m'];si=domain.get('segment_index',0)
        beds.append(dict(surface_id=surface_id,segment_index=si,polygon_xz_m=poly,
            vertex_y_m=[water_height_at(surface_id,*p,si)-depth for p in poly],
            height_api='water_height_at(surface_id,x,z,segment_index) - bed_depth_m',bed_depth_m=depth,
            lining_thickness_m=.3,buried_support_pitch_m=.5,lining_pitch_m=.1))
        for p,q in zip(poly,poly[1:]+poly[:1]):
            intervals=[]
            for other in domains:
                if other is domain:continue
                if not base._overlap(base._bounds([p,q]),base._bounds(other['polygon_xz_m'])):continue
                inside=base._line_inside_interval(p,q,other['polygon_xz_m'])
                if inside and inside[1]-inside[0]>1e-8:intervals.append(inside)
            for lo,hi in base._subtract_intervals([0,1],intervals):
                length=math.dist(p,q)*(hi-lo);n=max(1,math.ceil(length/2))
                for i in range(n):
                    ts=[lo+(hi-lo)*j/n for j in (i,i+1)]
                    ends=[[p[k]+(q[k]-p[k])*t for k in (0,1)] for t in ts]
                    ys=[water_height_at(surface_id,*v,si)-depth for v in ends]
                    tops=[land_height_at(*v) for v in ends]
                    banks.append(dict(from_xz_m=ends[0],to_xz_m=ends[1],bottom_y_m=ys,top_y_m=tops,
                        vertices_xyz_m=[[ends[0][0],ys[0],ends[0][1]],[ends[1][0],ys[1],ends[1][1]],
                                        [ends[1][0],tops[1],ends[1][1]],[ends[0][0],tops[0],ends[0][1]]],
                        thickness_m=.3,ownership='exterior wet/dry boundary only; no duplicate bend face'))
    interface=[]
    if surface_id=='SPRING_FEEDER':
        interface=[dict(id='FEEDER_RESERVOIR_SUBMERGED_BED_STEP',from_xz_m=[-1,-358],to_xz_m=[1,-358],
            top_y_m=15.4,bottom_y_m=13.6,water_y_m=16,head_drop_m=0,
            note='different bed depths at equal water head; submerged lining riser, not an invented waterfall')]
    return dict(surface_id=surface_id,beds=beds,exterior_banks=banks,bed_depth_interfaces=interface,
        status='finite source solids/face specification; not yet compiled or hydraulic validation',
        no_floating_water_rule='render/compile lining and banks with coarse buried support, not water-only plane over missing terrain')


def build_contract():
    _snapshot_check();current=json.loads((base.HERE/'contract.json').read_bytes())
    current.update(schema='riverstone.concept_city_v3.terrain_water.r04_ownership.v1',revision=4,
        base_contract_sha256=BASE_CONTRACT_SHA256,status='next_revision_bounded_source_only',
        compound_pads=compound_pads(),compound_candidates=compound_candidates(),building_pads=building_pads(),
        exact_surface_ownership=dict(api='surface_domains(bounds_xz_m)',maximum_query_span_m=32,
            height_api='surface_height_at(record,x,z)',
            precedence=['water_holes','actual_road','building_foundation_holes','whole_compound','stair_treads','paths','remaining_public_shoulders','terraces','base_ground'],
            bridge_rule='independent elevated deck domains from source bridges only; ground/water holes persist underneath',
            renderer_rule='clip owners before sampling; never use one composite boundary height for both sides of a retaining edge'),
        spring_feeder_support=channel_support_domains(),voxel_stage_plan=voxel_stage_plan(),
        access_rejections_from_independent_review=dict(
            source='validation/evidence/entrance_seams_b341bdf4547d_7b53ba97075c.json',
            additional_merchant_shops=['P_COURT_000:shop_residence_-1','P_COURT_000:shop_residence_1','P_COURT_001:shop_residence_-1','P_COURT_001:shop_residence_1'],
            measured_grades=[.2664,.3514],already_flagged_steps_or_replan_count=43,
            steepest_measured_grade=2.1778,policy='no cart/traversal approval; replace by compound floor only after every external frontage resolves'))
    return current


def main():
    contract=build_contract();(HERE/'contract.json').write_text(json.dumps(contract,indent=2,sort_keys=True)+'\n')
    patches={name:surface_domains(bounds) for name,bounds in [
        ('spring_basin_join',[-16,-384,16,-352]),('poor_court_gate',[112,272,144,304]),('noble_stair',[-360,40,-328,72]) ]}
    (HERE/'bounded_surface_domains.json').write_text(json.dumps(dict(source_plan_sha256=BASE_SOURCE_SHA256,patches=patches),indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(compound_pads=len(compound_pads()),accepted_poor=sorted(ACCEPTED_POOR_IDS),
        patches={k:len(v) for k,v in patches.items()},feeder_banks=len(contract['spring_feeder_support']['exterior_banks'])),indent=2))
if __name__=='__main__':main()
