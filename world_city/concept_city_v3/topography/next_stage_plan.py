"""Source-only voxel staging and parcel candidate budgets; never invokes a compiler."""
from __future__ import annotations
import json, math, hashlib
from . import author as a
from world_city.runtime_city.checks.placement import intersection_area


def _segments():
    for road in a.SOURCE_PLAN['roads']:
        for p,q in zip(road['polyline_xz_m'],road['polyline_xz_m'][1:]):
            if math.dist(p,q)>1e-8:yield road,p,q


def voxel_stage_plan():
    """Conservative counts before clipping overlaps, water, bodies and compounds."""
    bounds=[-608,-544,608,608];span=32;pitch=2;bottom=-8;top=28
    road_area=sum(math.dist(p,q)*(road['width_m']+4) for road,p,q in _segments())
    path_area=sum(math.dist(p,q)*(path['width_m']+1.2) for path in a.SOURCE_PLAN['paths']
                  for p,q in zip(path['polyline_xz_m'],path['polyline_xz_m'][1:]))
    cap_area=road_area+path_area
    maximum_resident_patches=16;patch_span=8;resident_area=maximum_resident_patches*patch_span**2
    counts=dict(rectangular_macro_chunks=math.ceil((bounds[2]-bounds[0])/span)*math.ceil((bounds[3]-bounds[1])/span),
        macro_candidate_cells_per_full_height_chunk=(span/pitch)**2*((top-bottom)/pitch),
        macro_candidate_cells_all_bounds=((bounds[2]-bounds[0])/pitch)*((bounds[3]-bounds[1])/pitch)*((top-bottom)/pitch),
        source_road_and_shoulder_area_sum_upper_bound_m2=road_area,
        source_path_and_transition_area_sum_upper_bound_m2=path_area,
        fine_area_sum_upper_bound_before_union_and_holes_m2=cap_area,
        full_network_fine_shell_cells_upper_bound=math.ceil(cap_area*.4/.1**3),
        full_network_thick_2_5m_micro_fill_cells_upper_bound_rejected=math.ceil(cap_area*2.5/.1**3),
        selected_review_fine_patch_count=maximum_resident_patches,
        selected_review_fine_patch_area_upper_bound_m2=resident_area,
        selected_review_fine_cap_cells_upper_bound=math.ceil(resident_area*.4/.1**3),
        selected_review_buffer_cells_upper_bound=math.ceil(resident_area*1.3/.2**3),
        selected_review_medium_support_cells_upper_bound=math.ceil(resident_area*2/.5**3))
    return dict(schema='riverstone.v3.next_voxel_stage_plan.v1',source_plan_sha256=a.SOURCE_PLAN_SHA256,
        status='source_budget_only_not_compiled',grid_origin_m=[0,0,0],bounds_xz_m=bounds,
        finite_source_bounds_xz_m=[-580,-520,580,590],chunk_span_m=span,
        boundary_planes='x=32*i and z=32*j, absolute world coordinates; identical names/values on adjacent chunks',
        terrain_y_envelope_m=[bottom,top],counts=counts,
        stages=[
          dict(id='macro',pitch_m=2,top_api='land_height_at minus owned promotion recesses',walk_collision=False,
               finite_exclusions=['water_domain_polygons','body foundations','compound source plot polygons'],
               note='unwalked earth remains macro; boundary bed/retaining geometry is separately owned'),
          dict(id='medium_support',pitch_m=.5,depth_below_cap_m=[1,3],
               ownership='entire macro recess guard, including the outer collar; no unfilled recess ring'),
          dict(id='buried_buffer',pitch_m=.2,depth_below_cap_m=[.2,1.5],
               ownership='promoted walk surface plus exact fine shoulder, overlapping support underground'),
          dict(id='fine_cap',pitch_m=.1,depth_m=.4,maximum_patch_span_m=8,
               ownership='selected source road/path/entry corridors plus exact owned shoulders only',
               collision='render voxel risers may reach .1 m; no automatic controller step-up claim'),
          dict(id='intentional_stairs',pitch_m=.05,source='neighborhood_stair_geometry',
               nominal_max_riser_m=.15,collision='explicit discrete treads/risers, separately tested from smooth cart collision')],
        promotion_rules=['clip and union exact source owners before counting/compiling',
            'subtract finite water holes unless an explicit bridge deck owns the span',
            'do not micro-fill parcels or every hill chunk',
            'atomic replacement: macro recess, medium guard support, buffer, fine cap and exposed retaining faces all present',
            'same global pitch/origin for peers; no per-chunk vertical offsets',
            'surface materials have disjoint exact XZ owners; no hidden-face removal unless emitted geometry proves it'],
        common_backend=['voxel_character.common.coordinate_planes.compile_master',
                        'existing common core', 'voxel_character.common.render_data'],
        adapter_work='A v3 facet adapter must sample/refine the current nonlinear height API inside exact finite owned polygons; old r2 default field/river metadata must not be reused.',
        collision_proxy=dict(type='finite continuous source-bound corridor collision',
            height_api='road_height_at / path_height_at',
            exclusions='all water and building/compound holes unless an explicit owned bridge/entrance surface exists',
            visible_support_required=True,stairs_not_smoothed=True,physics_status='not validated by this budget'),
        gates=['bounded 8 m patch master through common compiler',
            'shared-plane/source-H seam equality and actual exported cell occupancy',
            'bank/road outer-edge continuity and no poke-through',
            'capsule traversal on continuous ramp proxy; separate actual voxel-step test',
            'expand only after candidate cells and memory measured for bounded batch'])


def parcel_candidates():
    """Finite level-floor proposals, held outside the active frozen height field."""
    result=[];road_strips=[(r,a._strip(p,q,r['width_m']),a._strip(p,q,r['width_m']+4)) for r,p,q in _segments()]
    for plot in a.SOURCE_PLAN['plots']:
        if plot['property_type'] not in ['merchant_court','poor_block']:continue
        poly=plot['polygon_xz_m'];gate=plot['gate_position_xz_m'];floor=a.road_height_at(plot['road_id'],*gate)
        bounds=a._bounds(poly);samples=list(poly)+[gate]
        for x in range(math.ceil(bounds[0]),math.floor(bounds[2])+1,2):
            for z in range(math.ceil(bounds[1]),math.floor(bounds[3])+1,2):
                if a._inside(x,z,poly):samples.append([x,z])
        levels=[a.dry_height_at(*p) for p in samples];cut=max(0,max(levels)-floor);fill=max(0,floor-min(levels))
        road_overlap=0.;shoulder_overlap=0.
        for road,strip,shoulder in road_strips:
            if a._overlap(bounds,a._bounds(shoulder)):
                shoulder_overlap+=intersection_area(poly,shoulder)
                if a._overlap(bounds,a._bounds(strip)):road_overlap+=intersection_area(poly,strip)
        wet_overlap=sum(intersection_area(poly,w['polygon_xz_m']) for w in a.finite_water_domains()
                        if a._overlap(bounds,a._bounds(w['polygon_xz_m'])))
        yaw=plot['yaw_rad'];dx,dz=math.cos(yaw),-math.sin(yaw)
        gate_samples=[[gate[0]+i*dx,gate[1]+i*dz] for i in [-1.2,-.6,0,.6,1.2]]
        gate_heads=[a.road_height_at(plot['road_id'],*p) for p in gate_samples]
        max_gate_delta=max(abs(h-floor) for h in gate_heads)
        walls=[]
        for p,q in zip(poly,poly[1:]+poly[:1]):
            steps=max(1,math.ceil(math.dist(p,q)/2))
            for i in range(steps):
                p0=[p[k]+(q[k]-p[k])*i/steps for k in (0,1)]
                p1=[p[k]+(q[k]-p[k])*(i+1)/steps for k in (0,1)]
                if math.dist([(p0[k]+p1[k])/2 for k in (0,1)],gate)<1.6:continue
                walls.append(dict(from_xz_m=p0,to_xz_m=p1,pad_y_m=floor,
                    source_ground_y_m=[a.dry_height_at(*p0),a.dry_height_at(*p1)],thickness_m=.4))
        rejects=[]
        if max(cut,fill)>2:rejects.append('cut_or_fill_exceeds_2m_candidate_review_envelope')
        if road_overlap>1e-7:rejects.append('actual_road_overlap')
        if wet_overlap>1e-7:rejects.append('finite_water_overlap')
        if max_gate_delta>.02:rejects.append('level_gate_crossfall_requires_bounded_replan')
        result.append(dict(id=plot['id']+':COMPOUND_PAD_CANDIDATE',plot_id=plot['id'],property_type=plot['property_type'],
            status='rejected_pending_replan' if rejects else 'geometry_candidate_held_for_shoulder_ownership_decision',
            rejection_reasons=rejects,floor_y_m=floor,source_plot_polygon_xz_m=poly,owned_polygons_xz_m=[poly],
            maximum_cut_m=cut,maximum_fill_m=fill,foundation_bottom_y_m=min(floor,min(levels))-.4,
            sampled_source_ground_range_m=[min(levels),max(levels)],
            road_overlap_area_sum_m2=road_overlap,public_shoulder_overlap_area_sum_m2=shoulder_overlap,
            water_overlap_area_m2=wet_overlap,
            gate_ledger=[dict(id='main',xz_m=gate,threshold_y_m=floor,landing_y_m=floor,delta_m=0,
                full_width_sampled_delta_max_m=max_gate_delta,connection_xz_m=plot['gate_connection_xz_m'])],
            retaining_segments=walls,
            implementation_condition='whole plot is an explicit common property surface hole; a 2 m public shoulder cannot also claim that same polygon',
            future_entrances='all internal recipe doors use this single floor; boundary secondary exits must be declared and audited',
            engineering_safety='not assessed; 2 m is a gameplay/source-review envelope, not a structural rule'))
    return dict(schema='riverstone.v3.parcel_pad_candidates.v1',source_plan_sha256=a.SOURCE_PLAN_SHA256,
        active_height_field_changed=False,candidates=result)


def main():
    for name,data in [('voxel_stage_plan.json',voxel_stage_plan()),('parcel_pad_candidates.json',parcel_candidates())]:
        (a.HERE/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    print(json.dumps(voxel_stage_plan()['counts'],indent=2))
    print([(p['plot_id'],p['status'],p['rejection_reasons']) for p in parcel_candidates()['candidates']])

if __name__=='__main__':main()
