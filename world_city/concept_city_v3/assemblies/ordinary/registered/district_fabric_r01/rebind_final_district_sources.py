"""Final 24-source assembly: exact native cores, finite entries and rigid datums.

This producer writes only the additive ordinary source subtree.  R17 supplies
selected profile bytes and owns the finite terrain composition/release.
"""
from . import geometry as g
from .rebind_coherent_datums import shift, require
from .activate_backlands_subset import ActualNative, MaskIndex
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles, transform
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a
from collections import Counter
import copy, math, time, argparse

OUT=g.HERE/'final24_source_addendum_r01'
PREP=g.HERE/'final_source_preparation_r01/native_owner_replacements.json'
PREP_SHA='0f9a1514d90a4628105a4942d4e95fcac5828610b53a8e059abd1368db72859f'
ACTUAL=g.CITY/'evidence/r8_district_61_assembly_preflight_r01/scene.json'
STEP_HANDOFF=g.HERE/'final_pedestrian_step_skins_r01/native_step_handoff.json'
STEP_SHA='3ff5084861d7907f91b5b50d6e0bf66d8a8fdbd4b49ba6198c301535e1d91480'
INNER_HANDOFF=g.HERE/'final_inner_entry_chains_r01/handoff.json'
WITHDRAWAL=g.HERE/'b08_market_hall_withdrawal_r01/handoff.json'
ACTUAL_SHA='643851e9554c335fc5af4f1e1b6b51af19d3e67b4b1bc578c091539f29a29299'

def area(polys): return sum(g.geo.polygon_area(q) for q in polys)
def refify(path): return g.ref(path)
def bearings_for(ps, assets, floor, hid):
    owners=[];bearings=[]
    for p in ps:
        asset=assets[p['asset_key']];bb=asset.get('bounds') or g.load(g.ROOT/asset['render_path'])['bounds']
        p['native_bottom_y_m']=p['position_m'][1]+bb['min'][1]
        p['dimensions_m']=[bb['max'][i]-bb['min'][i] for i in range(3)]
        p['holding_floor_y_m']=floor
        p['exterior_access']=dict(implementation_tier='exterior_only',actual_entrance_ids=p.get('actual_door_ids',[]),holding_id=hid)
        owners.append(dict(id=p['id'],asset_key=p['asset_key'],render_sha256=asset['render_sha256'],position_m=p['position_m'],yaw_rad=p['yaw_rad'],scale=[1,1,1],native_bottom_y_m=p['native_bottom_y_m'],polygons_xz_m=p['native_foundation_polygons_xz_m']))
        for j,q in enumerate(p['native_foundation_polygons_xz_m']):
            bearings.append(dict(id=p['id']+f':{j}',holding_id=hid,polygon_xz_m=q,floor_y_m=floor,native_bottom_y_m=p['native_bottom_y_m'],embedded_depth_m=floor-p['native_bottom_y_m'],outside_logical_earth_owner_m2=0.))
    return owners,bearings

def load_sources(req, ids):
    mf=require(req.get('effective_city_manifest',g.ref(g.HERE/'effective_city_manifest_r01.json')))
    layout=require(req['source_layout']);prepared=require(req['source_prepared_parcels'])
    byholding={h['id']:h for h in layout['holdings']};byparcel={p['id']:p for p in prepared['parcels']}
    retrows={r['source_id']:r for r in prepared['retirement_records']};sources={}
    for d in mf['districts']:
        if d['block_id']=='BLOCK_007' or not any(i.startswith(d['block_id']+':') for i in ids):continue
        root=(g.ROOT/d['pack']['path']).parent
        sources[d['block_id']]=dict(pack=require(d['pack']),access=g.load(root/'access_handoff.json'),terrain=g.load(root/'terrain_handoff.json'),equipment=g.load(root/'court_equipment.json'),refs=dict(pack=d['pack'],access=g.ref(root/'access_handoff.json'),terrain=g.ref(root/'terrain_handoff.json'),equipment=g.ref(root/'court_equipment.json')))
    if any(i.startswith('BLOCK_007:') for i in ids):
        root=g.HERE/'b07_terrace_refit_r02/BLOCK_007'
        src={k:g.load(root/f) for k,f in [('pack','resolved_placements.json'),('access','access_handoff.json'),('terrain','terrain_handoff.json'),('equipment','court_equipment.json'),('layout','selected_layout.json')]}
        src['refs']={k:g.ref(root/f) for k,f in [('pack','resolved_placements.json'),('access','access_handoff.json'),('terrain','terrain_handoff.json'),('equipment','court_equipment.json'),('layout','selected_layout.json')]}
        sources['BLOCK_007']=src;byholding.update({h['id']:h for h in src['layout']['holdings']});byparcel.update({p['id']:p for p in src['terrain']['parcels']});retrows.update({r['source_id']:r for r in src['terrain']['retirement_records']})
    return mf,layout,prepared,byholding,byparcel,retrows,sources

def public_binding(holding, profile, pref, candidate=None):
    old=copy.deepcopy(holding.get('public_target_evidence'))
    if candidate and 'polyline_xz_m' in candidate:
        holding.update(external_route=candidate['polyline_xz_m'],external_route_polygons_xz_m=candidate['polygons_xz_m'],external_width_m=candidate['width_m'],public_road_id=candidate['public_road_id'])
    line=holding['external_route'];target=line[-1]
    fixed=profile.get('public_fixed_regions', profile.get('fixed_public_regions', []))
    if not fixed and candidate:fixed=candidate.get('fixed_public_regions',[])
    holding['public_target_xz_m']=target
    holding['public_target_evidence']=dict(point_xz_m=target,selected_finite_profile=pref,fixed_public_regions=fixed,previous_source_evidence=old,evidence_policy='Selected finite public planes and terminal are authoritative; historical source-road estimate is provenance only.')
    holding['public_join_status']='Selected finite profile is source-bound. Final terrain/native-side composition and actual controller replay remain separate gates.'


def function_contract(h, ps, doors, routes, profile):
    poly=h['holding_polygon_xz_m'];dims=sorted([math.dist(poly[i],poly[(i+1)%len(poly)]) for i in range(min(4,len(poly)))])
    inner=min((r['width_m'] for r in routes),default=h['external_width_m'])
    limit=profile.get('grade_limit') or profile.get('result',{}).get('grade_limit')
    if not limit and isinstance(profile.get('result',{}).get('result'),dict):limit=profile['result']['result'].get('grade_limit')
    h['exterior_function_contract']=dict(implementation_tier='exterior_only',planned_role=h.get('planned_role'),holding_width_m=dims[0],holding_depth_m=dims[-1],floor_y_m=h['floor_y_m'],actual_entrance_ids=[d['id'] for d in doors],native_component_ids=[p['id'] for p in ps if ':FABRIC:' in p['id']],public_road_id=h['public_road_id'],gate_xz_m=h['gate_position_xz_m'],external_route_width_m=h['external_width_m'],minimum_internal_pedestrian_width_m=inner,cart_access_claim=bool(h.get('cart_access_into_inner_court',False)),declared_external_grade_limit=limit,roof_palette_ids=sorted({p['palette_id'] for p in ps if p.get('palette_id')}),commerce_simulation=False,open_interior_claim=False)
    if 'flat_owner_polygons_xz_m' in h:
        h['design']='Reusable native ranges around an explicit compact flat court, with a separately graded pedestrian entry and retained source-plane margins.'
        h['exterior_function_contract']['cart_access_claim']=False
    return h


def run(request_path, expected):
    started=time.monotonic();request_path=g.ROOT/request_path if not request_path.is_absolute() else request_path
    assert g.ref(request_path)['sha256']==expected
    req=g.load(request_path);reqref=g.ref(request_path);ids=set(req['matched_next_batch_holding_ids']);assert len(ids)==23 and 'BLOCK_008:R8_C003' not in ids
    assert g.ref(PREP)['sha256']==PREP_SHA and g.ref(ACTUAL)['sha256']==ACTUAL_SHA
    assert g.ref(STEP_HANDOFF)['sha256']==STEP_SHA
    prep=g.load(PREP);revised={r['holding_id']:r for r in prep['records']};assert set(revised)<=ids
    mf,layout,prepared,byholding,byparcel,retrows,sources=load_sources(req,ids)
    innerdata=g.load(INNER_HANDOFF);assert innerdata['passed'];inners={r['holding_id']:r for r in innerdata['records']};withdrawal=g.load(WITHDRAWAL);assert withdrawal['passed']
    changes={r['holding_id']:r for r in req['datum_changes']};records=[];assets={};allps=[];alldoors=[];allroutes=[];allbearings=[];retire=set();deferred=[];source_superseded=[]
    for hid in sorted(ids):
        src=sources[hid.split(':')[0]];old=byholding[hid];ch=changes.get(hid);delta=ch['delta_y_m'] if ch else 0.;floor=ch['candidate_floor_y_m'] if ch else old['floor_y_m']
        if ch:assert abs(old['floor_y_m']-ch['original_floor_y_m'])<1e-9
        profile_ref=req['profile_bindings'][hid];profile=require(profile_ref)
        oldps=[p for p in src['pack']['placements'] if p.get('holding_id')==hid]
        originaldoors=[d for d in src['pack']['actual_doors'] if d['holding_id']==hid]
        h=shift(old,delta);ps=shift(oldps,delta);doors=shift(originaldoors,delta);routes=shift([r for r in src['access']['routes'] if r['holding_id']==hid],delta)
        parcel=shift(byparcel[hid],delta);ground=shift(next(x for x in src['equipment']['holding_grounds'] if x['holding_id']==hid),delta);chain=shift(next(x for x in src['terrain']['court_route_chains'] if x['holding_id']==hid),delta)
        localassets=dict(src['pack']['assets']);candidate=None;deferred_here=[]
        if hid in revised:
            rr=revised[hid];candidate=next(r for r in require(rr['selected_candidate'])['records'] if r['holding_id']==hid)
            assert abs(candidate['floor_y_m']-floor)<1e-9, (hid,candidate['floor_y_m'],floor)
            h=copy.deepcopy(rr['replacement_holding']);ps=copy.deepcopy(rr['replacement_native_placements']);doors=copy.deepcopy(rr['replacement_actual_doors']);routes=copy.deepcopy(rr['replacement_door_routes']);localassets.update(rr['assets']);deferred_here=copy.deepcopy(rr['explicit_deferred_source_placements'])
            source_superseded.extend(rr['superseded_unactivated_source_native_ids'])
            flat=h['flat_owner_polygons_xz_m'];margins=h['surface_following_margin_polygons_xz_m'];prof=h['profile_domain_polygons_xz_m'];visible=rr['flat_visible_ground_polygons_xz_m'];feet=[q for p in ps for q in p['native_foundation_polygons_xz_m']]
            ground.update(finished_floor_y_m=floor,polygon_parts_xz_m=visible,native_hole_polygons_xz_m=feet,equipment_placement_ids=[p['id'] for p in ps if ':FABRIC:' not in p['id']],boundary_segments=sum(':BOUNDARY:' in p['id'] for p in ps),flat_owner_polygons_xz_m=flat,profile_domain_polygons_xz_m=prof,surface_following_margin_polygons_xz_m=margins,shared_inner_seams_xz_m=h['shared_inner_seams_xz_m'],boundary_status=rr['boundary_continuity_policy'],core_court_polygons_xz_m=h['core_court_polygons_xz_m'],previous_source_open_boundary_intervals=ground.get('open_boundary_intervals',[]),open_boundary_intervals=[],ground_mode='EXPLICIT_FLAT_NATIVE_CORE_WITH_SEPARATE_FINITE_ENTRY_AND_SOURCE_PLANE_MARGIN')
            parcel.update(flat_owner_polygons_xz_m=flat,profile_domain_polygons_xz_m=prof,surface_following_margin_polygons_xz_m=margins,shared_inner_seams_xz_m=h['shared_inner_seams_xz_m'],whole_holding_polygons_xz_m=[h['holding_polygon_xz_m']],ground_owner=ground,ground_mode=ground['ground_mode'],court_polygons_xz_m=h['core_court_polygons_xz_m'])
        elif 'candidate' in profile and 'polyline_xz_m' in profile['candidate']:
            candidate=profile['candidate'];assert candidate['gate_xz_m']==h['gate_position_xz_m'] and abs(candidate['floor_y_m']-floor)<1e-9
            mi=MaskIndex([dict(id='SELECTED_NEW_ENTRY',polygon_xz_m=q) for q in candidate['polygons_xz_m']]);keep=[]
            for p in ps:
                if not mi.hit(p['native_walking_obstacles_xz_m']):keep.append(p);continue
                assert ':FABRIC:' not in p['id'],('Native building intersects selected entry',p['id'])
                deferred_here.append(dict(id=p['id'],asset_key=p['asset_key'],reason='INTENTIONAL_ENTRY_OPENING' if ':BOUNDARY:' in p['id'] else 'FIXTURE_INTERSECTS_SELECTED_ENTRY',original_placement=next(x for x in oldps if x['id']==p['id'])))
            ps=keep;holes=[q for p in ps for q in p['native_foundation_polygons_xz_m']];restore=[q for p in deferred_here for q in p['original_placement']['native_foundation_polygons_xz_m']]
            ground['polygon_parts_xz_m']=a.common.subtract(a.common.disjoint_union(ground['polygon_parts_xz_m']+restore),holes);ground['native_hole_polygons_xz_m']=holes;ground['equipment_placement_ids']=[p['id'] for p in ps if ':FABRIC:' not in p['id']];ground['boundary_segments']=sum(':BOUNDARY:' in p['id'] for p in ps)
            if deferred_here:ground['intentional_gate_opening']=dict(route=candidate['polygons_xz_m'],deferred_panel_ids=[p['id'] for p in deferred_here if ':BOUNDARY:' in p['id']],fully_enclosed_claim=False)
        public_binding(h,profile,profile_ref,candidate if candidate and 'polyline_xz_m' in candidate else None)
        if ch:h['court_datum_evidence']=dict(previous_source_evidence=old.get('court_datum_evidence'),floor_y_m=floor,rigid_y_delta_m=delta,request=reqref)
        owners,bearings=bearings_for(ps,localassets,floor,hid);feet=[q for p in ps for q in p['native_foundation_polygons_xz_m']]
        parcel.update(floor_y_m=floor,footing_polygons_xz_m=feet,native_footing_owners=owners,actual_door_ids=[d['id'] for d in doors],walk_polygons_xz_m=[q for r in routes for q in r['polygons_xz_m']]+h['external_route_polygons_xz_m'],ground_owner=ground,public_road_id=h['public_road_id'],public_target_evidence=h['public_target_evidence'],entry_width_m=h['external_width_m'],selected_external_profile=profile_ref)
        chain.update(door_link_ids=[r['id'] for r in routes],external_gate_route_id=hid+':GATE_LINK',gate_xz_m=h['gate_position_xz_m'],route_ids_to_public=[hid+':GATE_LINK'],public_root=dict(node_id=hid+':GATE_LINK',public_road_id=h['public_road_id'],public_center_anchor=h['public_target_evidence'],proposed_floor_y_m=floor,selected_external_profile=profile_ref),status='Exact source-bound finite entry; final composed side/support/controller gate pending')
        h=function_contract(h,ps,doors,routes,profile)
        checks=dict(all_unit_scale=all(p['scale']==[1,1,1] for p in ps),all_doors_at_floor=all(abs(d['actual_door_xyz_m'][1]-floor)<1e-8 for d in doors),all_internal_routes_at_floor=all(abs(r['floor_y_m']-floor)<1e-8 and all(abs(q[1]-floor)<1e-8 for q in r['polyline_xyz_m']) for r in routes),all_bearings_consistent=all(abs(b['native_bottom_y_m']+b['embedded_depth_m']-floor)<1e-8 for b in bearings),target_equals_selected_route_endpoint=h['public_target_xz_m']==h['external_route'][-1],source_retirement_set_unchanged=parcel['retired_source_ids']==byparcel[hid]['retired_source_ids'],all_expected_door_ids_bound=set(parcel['actual_door_ids'])==set(d['id'] for d in doors))
        if hid in revised:
            checks['all_feet_inside_explicit_flat_union']=area(a.common.subtract(feet,h['flat_owner_polygons_xz_m']))<1e-7
            checks['all_door_ribbons_inside_explicit_flat_union']=area(a.common.subtract([q for r in routes for q in r['polygons_xz_m']],h['flat_owner_polygons_xz_m']))<1e-7
            checks['complete_old_enclosure_held']=not any(':BOUNDARY:' in p['id'] for p in ps)
        else:
            oldbyid={p['id']:p for p in oldps};checks['all_unchanged_native_poses_rigid']=all(p['position_m'][::2]==oldbyid[p['id']]['position_m'][::2] and abs(p['position_m'][1]-oldbyid[p['id']]['position_m'][1]-delta)<1e-8 and p['yaw_rad']==oldbyid[p['id']]['yaw_rad'] for p in ps)
        if not all(checks.values()):raise ValueError((hid,checks))
        if hid in inners:
            inner=copy.deepcopy(inners[hid]);inner['selected_external_profile']=profile_ref;h['inner_flat_to_gate_route']=inner
            chain['inner_flat_to_gate_route_id']=inner['id'];chain['route_ids_to_public']=[inner['id'],hid+':GATE_LINK']
        record=dict(holding_id=hid,old_floor_y_m=old['floor_y_m'],new_floor_y_m=floor,rigid_y_delta_m=delta,source_bindings=src['refs'],selected_native_source=revised[hid]['selected_candidate'] if hid in revised else src['refs']['pack'],replacement_holding=h,replacement_terrain_parcel=parcel,replacement_holding_ground=ground,replacement_native_placements=ps,replacement_actual_doors=doors,replacement_door_routes=routes,replacement_court_route_chain=chain,replacement_native_earth_bearings=bearings,selected_external_profile=profile_ref,explicit_deferred_source_placements=deferred_here,superseded_unactivated_source_native_ids=revised[hid]['superseded_unactivated_source_native_ids'] if hid in revised else [],checks=checks,passed=True)
        if hid in inners:record['replacement_inner_entry_route']=h['inner_flat_to_gate_route']
        if hid=='BLOCK_001:R8_C003':record['replacement_profile_native_extension']=g.ref(STEP_HANDOFF)
        records.append(record);allps+=ps;alldoors+=doors;allroutes+=routes;allbearings+=bearings;retire.update(parcel['retired_source_ids']);deferred.extend(dict(x,holding_id=hid) for x in deferred_here)
        for p in ps:assets[p['asset_key']]=localassets[p['asset_key']]
    assert retire==set(req['exact_retirement_ids']),(sorted(retire-set(req['exact_retirement_ids'])),sorted(set(req['exact_retirement_ids'])-retire))
    assert len({p['id'] for p in allps})==len(allps) and len({d['id'] for d in alldoors})==len(alldoors)
    OUT.mkdir(exist_ok=True)
    output=dict(schema='riverstone.district_fabric.final_atomic_native_and_entry_batch.v1',request=reqref,source_layout=req['source_layout'],source_prepared_parcels=req['source_prepared_parcels'],final_native_owner_preparation=g.ref(PREP),base_scene=g.ref(g.R7),base_actual_native_scene=g.ref(ACTUAL),records=records,matched_next_batch_holding_ids=sorted(ids),datum_changes=req['datum_changes'],assets=assets,placements=allps,actual_doors=alldoors,door_routes=allroutes,native_earth_bearings=allbearings,retired_source_ids=sorted(retire),retired_foundation_proxy_ids=[i+':owned_foundation' for i in sorted(retire)],retirement_records=[retrows[i] for i in sorted(retire)],profile_bindings=req['profile_bindings'],superseded_unactivated_source_native_ids=sorted(set(source_superseded)),explicit_deferred_source_placements=deferred,palette_semantic_mapping=mf.get('palette_semantic_mapping',next(iter(sources.values()))['pack'].get('palette_semantic_mapping')),profile_native_extensions=[g.ref(STEP_HANDOFF)],inner_entry_routes=[r['replacement_inner_entry_route']for r in records if 'replacement_inner_entry_route'in r],inner_entry_handoff=g.ref(INNER_HANDOFF),superseded_domain_handoffs=[g.ref(WITHDRAWAL)],completed_source_milestone=dict(adopted_new_holdings=23,accounted_superseded_domains=1,unresolved_holdings=0),implementation_tier='exterior_only',activation=False,new_compilations=1,status='SOURCE_ASSEMBLED_PENDING_INDEPENDENT_NATIVE_AUDIT',summary=dict(holdings=len(records),native_core_refits=len(revised),native_placements=len(allps),native_range_assemblies=sum(':FABRIC:' in p['id'] for p in allps),actual_doors=len(alldoors),internal_routes=len(allroutes),native_bearings=len(allbearings),old_native_retirements=len(retire),deferred_unactivated_boundary_panels=sum(':BOUNDARY:' in p['id'] for p in deferred),deferred_unactivated_other_fixtures=sum(':BOUNDARY:' not in p['id'] for p in deferred),additional_profile_native_step_placements=1,new_compilations=1,seconds=time.monotonic()-started),integration_rules=['Apply all 23 holding/native/door/route/bearing and old-owner retirements atomically with the matching R17 terrain batch.','Eight revised owners have explicit disjoint flat support, finite profile and source-plane margin partitions. Never restore the obsolete whole-rectangle flat constraint.','Deferred source panels and fixtures were not active scene objects. Their old proposal holes are cancelled, rather than retired from the current scene.','Cache scale, palette semantic mapping and source bytes remain fixed. Actual exterior doors and selected finite public terminals remain authoritative.','Pedestrian-only interior entries and the explicitly authorized stepped/sloped exceptions do not imply cart access or an open building interior.'])
    g.write(OUT/'atomic_source_addendum.json',output);print(output['summary'],flush=True);print(g.ref(OUT/'atomic_source_addendum.json'),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('request');parser.add_argument('sha256');args=parser.parse_args();run(g.Path(args.request),args.sha256)
