"""Finite, source-only water graph. No city edits, meshing, or hydraulics solver.

All elevations are world metres, +Y up. Positive endpoint head is necessary,
not sufficient, for gravity operation. This module deliberately cannot promote
its candidate into the frozen scene.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from world_city.runtime_city.topography import author as terrain

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BRIEF = ROOT / 'world_city/data/city_brief.v2.json'
SCENE = ROOT / 'world_city/runtime_city/generated/r2/scene.graded_property.json'
CANDIDATE = HERE / 'hydrology_candidate.json'
GRAVITY = {'gravity', 'controlled_drop', 'overflow_air_gap', 'mill_head_drop'}


def rectangle(a, b, width):
    dx, dz = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx,dz)
    if length <= 0 or width <= 0: raise ValueError('nonzero segment and width required')
    nx, nz = -dz/length*width/2, dx/length*width/2
    return terrain._convex([[a[0]+nx,a[1]+nz],[a[0]-nx,a[1]-nz],
                            [b[0]-nx,b[1]-nz],[b[0]+nx,b[1]+nz]])


def hull(points):
    pts=sorted(set(tuple(p) for p in points))
    def cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def half(ps):
        h=[]
        for p in ps:
            while len(h)>1 and cross(h[-2],h[-1],p)<=0: h.pop()
            h.append(p)
        return h
    return [list(p) for p in half(pts)[:-1]+half(reversed(pts))[:-1]]


def _sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def build_candidate():
    brief=json.loads(BRIEF.read_text()); scene=json.loads(SCENE.read_text())
    field=terrain.field_from_brief(brief)
    nodes=[]; edges=[]
    def node(id, x, z, head, network, kind, assumption, **kw):
        record=dict(id=id, xz_m=[x,z], reference_y_m=head,
                    reference_kind='candidate_water_surface_or_hydraulic_grade',
                    source_ground_y_m=round(field.height(x,z),9), network=network,
                    kind=kind, elevation_basis=assumption, geometry_status='unbuilt_candidate',
                    water_quality='unverified_not_certified_potable')
        record.update(kw);nodes.append(record);return id
    def edge(id, a, b, mode='gravity', scenario='local_supply_and_drainage', **kw):
        na=next(n for n in nodes if n['id']==a);nb=next(n for n in nodes if n['id']==b)
        e=dict(id=id, source=a, target=b, mode=mode, scenario=scenario,
               profile_xyz_m=[[na['xz_m'][0],na['reference_y_m'],na['xz_m'][1]],
                              [nb['xz_m'][0],nb['reference_y_m'],nb['xz_m'][1]]],
               alignment_status='logical_profile_only_not_clearance_approved',
               hydraulic_capacity_status='unverified', built=False)
        e.update(kw);edges.append(e)
    # Local high-quarter supply does not assume that water can climb from the river.
    for prefix,x,z,ground,roof,well in [('CASTLE',-430,-330,24,32,10),
                                      ('CATHEDRAL',350,-300,14,22,4),
                                      ('MARKET',-20,0,0,8,-5)]:
        net='protected_supply_'+prefix.lower()
        node(prefix+'_ROOF',x,z,roof,net,'roof_collection',
             'authored gutter height; roof collection area and rainfall yield unverified')
        node(prefix+'_CISTERN',x+12,z+8,ground-1.2,net,'covered_storage',
             'authored buried cistern operating water level; no capacity or lining validation',
             cover_crest_y_m=ground+.2, bottom_y_m=ground-3.2)
        node(prefix+'_WELL',x-8,z+12,well,net,'hypothetical_groundwater',
             'illustrative groundwater head only; aquifer existence and yield NOT established')
        node(prefix+'_DRAW',x+8,z+15,ground+.8,net,'hand_lifted_draw_basin',
             'authored basin lip; bucket/windlass lifts explicitly supply energy')
        node(prefix+'_USE',x+9,z+16,ground+.4,net,'local_draw_point',
             'authored local use basin; water quality unverified')
        node(prefix+'_STORM',x+10,z+18,ground-.25,'storm','separate_gutter',
             'authored storm inlet invert',reference_kind='drain_invert')
        edge(prefix+'_RAIN',prefix+'_ROOF',prefix+'_CISTERN')
        edge(prefix+'_CISTERN_LIFT',prefix+'_CISTERN',prefix+'_DRAW','manual_lift',
             energy_source='human_bucket_or_windlass', gravity_claim=False)
        edge(prefix+'_WELL_LIFT',prefix+'_WELL',prefix+'_DRAW','manual_lift',
             energy_source='human_bucket_or_windlass', gravity_claim=False)
        edge(prefix+'_DISTRIBUTE',prefix+'_DRAW',prefix+'_USE')
        edge(prefix+'_OVERFLOW',prefix+'_DRAW',prefix+'_STORM','overflow_air_gap',
             separation='one_way_air_gap_no_storm_to_supply_connection')
    # Separate drainage: no cross-connection back into protected supply.
    node('STORM_COLLECTOR',200,160,-.70,'storm','drain_junction',
         'candidate drain invert; underground alignment/foundation conflicts unresolved',reference_kind='drain_invert')
    node('STORM_DOWNSTREAM',460,330,-1.20,'storm','drain_junction',
         'candidate drain invert; separate from industrial water',reference_kind='drain_invert')
    node('STORM_OUTFALL',670,450,-1.55,'storm','free_outfall_candidate',
         'candidate outlet invert; flood backwater and river stage unverified',reference_kind='drain_invert')
    node('RIVER_RECEIVER',670,450,-2.11,'receiving_water','river_reference',
         'parent-requested r3 design reference, NOT frozen scene water elevation',
         frozen_r2_authored_water_surface_y_m=scene['infrastructure']['river']['water_surface_y_m'])
    for p in ('CASTLE','CATHEDRAL','MARKET'):edge(p+'_DRAIN',p+'_STORM','STORM_COLLECTOR')
    edge('STORM_MAIN','STORM_COLLECTOR','STORM_DOWNSTREAM')
    edge('STORM_OUT','STORM_DOWNSTREAM','STORM_OUTFALL')
    edge('STORM_RIVER','STORM_OUTFALL','RIVER_RECEIVER',receiving_stage_envelope_unverified=True)
    node('WASTE_VAULT',440,170,-.8,'contained_waste','sealed_or_lined_vault_candidate',
         'source-only waste storage marker; location, seepage and lining unverified')
    node('WASTE_COLLECTION',450,180,.2,'contained_waste','manual_removal_endpoint',
         'removal operation only; offsite destination remains unresolved')
    edge('WASTE_REMOVE','WASTE_VAULT','WASTE_COLLECTION','manual_removal',
         energy_source='human_or_cart', gravity_claim=False,
         destination_status='offsite_disposal_not_designed_no_river_discharge_edge')
    # Authored alternative B: entirely new headwaters/NE landform, never assumed existing.
    scenario='authored_ne_tributary_reservoir_and_working_canal'
    for id,x,z,head,kind in [
        ('NE_SOURCE',520,-620,20,'new_external_spring_or_tributary'),
        ('NE_INTAKE',515,-590,19.8,'screened_split_intake'),
        ('NE_RESERVOIR',500,-480,15.6,'industrial_storage_pond'),
        ('DROP_UPPER',555,-350,8,'controlled_drop_pool'),
        ('DROP_LOWER',578,-270,2,'controlled_drop_pool'),
        ('RACE_NORTH',580,-198,.8,'regulating_forebay'),
        ('RACE_A',584,-54,.7,'lined_working_canal'),
        ('RACE_B',512,154,.55,'lined_working_canal'),
        ('RACE_C',528,170,.5,'lined_working_canal'),
        ('MILL_FOREBAY',540,280,.4,'new_optional_mill_forebay'),
        ('MILL_TAIL',570,328,-1.1,'new_optional_mill_tailrace')]:
        node(id,x,z,head,'industrial_nonpotable',kind,
             'explicit r3 authored alternative; source flow, storage yield and hydraulic behavior unverified',
             scenario=scenario)
    chain=['NE_SOURCE','NE_INTAKE','NE_RESERVOIR','DROP_UPPER','DROP_LOWER',
           'RACE_NORTH','RACE_A','RACE_B','RACE_C','MILL_FOREBAY','MILL_TAIL','RIVER_RECEIVER']
    for i,(a,b) in enumerate(zip(chain,chain[1:])):
        mode=('controlled_drop' if a in {'NE_RESERVOIR','DROP_UPPER','DROP_LOWER'} else
              'mill_head_drop' if a=='MILL_FOREBAY' else 'gravity')
        edge('NE_%02d'%i,a,b,mode,scenario,alignment_status='exact_candidate_reservation_audited_below',
             owned_corridor_width_m=6, proposed_open_water_width_m=2,
             bank_or_access_width_each_side_m=2,
             separation='industrial_nonpotable_no_direct_drinking_connection')
    # Separate covered supply takes raw water upstream of the working pond. The
    # screened intake is NOT purification. No conduit from the industrial pond.
    node('NE_COVERED_HEADER',505,-570,19.2,'protected_supply_candidate','separate_covered_header',
         'new covered header upstream of industrial reservoir; raw-water quality unverified',scenario=scenario)
    node('CATHEDRAL_SUPPLY_ENTRY',430,-400,15.0,'protected_supply_candidate','covered_conduit_entry',
         'new wall penetration / covered trench required; route conflicts remain unapproved',scenario=scenario)
    edge('NE_SUPPLY_SPLIT','NE_INTAKE','NE_COVERED_HEADER','gravity',scenario,
         separation='raw_source_split_before_industrial_use_not_purification')
    edge('NE_COVERED_CONDUIT','NE_COVERED_HEADER','CATHEDRAL_SUPPLY_ENTRY','gravity',scenario,
         construction='covered_trench_or_embedded_conduit_requires_new_ne_terrain_no_roman_arcade_assumption')
    edge('NE_CATHEDRAL_FILL','CATHEDRAL_SUPPLY_ENTRY','CATHEDRAL_CISTERN','gravity',scenario,
         separation='protected_branch_raw_water_quality_unverified')
    graph=dict(schema='riverstone.city.hydrology_candidate.v1', revision=3,
        status='source_only_unbuilt_requires_concept_choice',
        coordinate_system={'axes':'Y_up_XZ_plan','units':'metres','grid_origin_m':[0,0,0]},
        sources={'brief':str(BRIEF.relative_to(ROOT)),'brief_sha256':_sha(BRIEF),
                 'frozen_scene':str(SCENE.relative_to(ROOT)),'frozen_scene_sha256':_sha(SCENE)},
        datum={'castle_ground_m':24,'cathedral_ground_m':14,'market_ground_m':0,
               'frozen_r2_authored_river_surface_m':-2,'r3_river_design_reference_m':-2.11,
               'river_reference_difference_m':-.11,'r2_modified':False},
        evidence={'observed_in_revision_02_image':['raised castle and cathedral','small planted terraces'],
                  'not_measured_from_image':['water sources','reservoir levels','channel grades','well yields'],
                  'all_new_water_dimensions':'fictional game-design assumptions, not historical measurements'},
        nodes=nodes,edges=edges,
        alternatives=[
            {'id':'A','name':'local_supply_and_drainage','selection':'compatible source-only baseline',
             'new_headwaters_required':False,'visible_canal':False},
            {'id':'B','name':scenario,'selection':'workable elevation-graph candidate awaiting concept choice',
             'new_headwaters_required':True,'visible_canal':True,'hydraulic_validation':False},
            {'id':'C','name':'flat_river_fed_gravity_race','selection':'rejected under current flat-river premise',
             'intake_water_y_m':-2.11,'desired_forebay_y_m':.4,'tailwater_y_m':-2.11,
             'intake_to_forebay_head_m':-2.51,'river_to_same_river_gross_head_m':0,
             'reason':'river cannot gravity-feed +0.4 m forebay; equal flat intake/tailwater gives zero gross head'},
            {'id':'D','name':'new_weir_or_upstream_river_gradient','selection':'separate unchosen major river-remodel alternative',
             'example_intake_water_y_m':.8,'tailwater_y_m':-2.11,'example_gross_head_m':2.91,
             'requirements':['new river longitudinal profile or impoundment','flood/backwater/storage assessment',
                             'revised banks/bridges/intakes','explicit river revision approval']}],
        protected_existing_mill={'id':'D06-B052','power':'animal_or_manual',
                                 'change':'none; optional new wheel site is separate'},
        unresolved=['spring/tributary existence and perennial flow','all drinking-water quality',
                    'roof catchment and dry-period supply','groundwater levels and yields',
                    'reservoir liner/embankment stability, seepage and spillway',
                    'flow capacity, velocity, sediment, erosion, flood/backwater and operating controls',
                    'all underground conduit/drain alignment and foundation conflicts',
                    'land-use/courtyard reservations and bridge/water-gate redesign',
                    'offsite waste removal destination'],
        integration_contract={'automatic_promotion_forbidden':True,'new_geometry':False,
            'compiler':'existing common coordinate_planes/core/render_data only',
            'finite_ground_domain_changes':'only explicit approved reservoir/corridor/headwater polygons; subtract original ownership first',
            'frozen_river_holes':'preserve exact existing river exclusions; outfall meets shoreline through separate connector',
            'layers':'macro ground + medium canal banks/support + bounded fine walking caps/bridges; never citywide fine fill',
            'grid':'world XZ, identity placement, global grid origin [0,0,0]; shared boundary planes reserved',
            'collision':'water is not walkable terrain; guard/bridge/gate/stair hooks need separate semantic checks',
            'depth':'no coplanar terrain/water/plaza faces; excavate channel ownership and use explicit liners',
            'hidden_faces':'no hidden-face removal claim; no geometry has been compiled'})
    # Exact owned horizontal candidate domains. Union semantics, not summed areas.
    index={n['id']:n for n in nodes};domains=[];bands=[]
    for e in edges:
        if not e['id'].startswith('NE_') or 'owned_corridor_width_m' not in e: continue
        poly=rectangle(index[e['source']]['xz_m'],index[e['target']]['xz_m'],6)
        bands.append(poly);domains.append({'id':e['id']+'_DOMAIN','edge_id':e['id'],
            'polygon_xz_m':poly,'role':'candidate_canal_and_bank_reservation','edit_status':'not_applied'})
    for i in range(len(bands)-1):
        poly=hull(bands[i][-2:]+bands[i+1][:2])
        if len(poly)>=3 and abs(terrain._area(poly))>1e-8:
            domains.append({'id':'NE_JOIN_%02d'%i,'polygon_xz_m':poly,'role':'exact_owned_bend_join','edit_status':'not_applied'})
    domains.append({'id':'NE_RESERVOIR_DOMAIN','polygon_xz_m':[[470,-505],[530,-505],[530,-455],[470,-455]],
        'role':'reservoir_water_and_bank_outer_reservation','edit_status':'not_applied',
        'water_footprint_xz_m':[[476,-499],[524,-499],[524,-461],[476,-461]],
        'candidate_water_y_m':15.6,'candidate_bottom_y_m':13.6,'candidate_bank_crest_y_m':16.4,
        'spillway_capacity_and_freeboard_validation':False})
    domains.append({'id':'NE_HEADWATER_DOMAIN','polygon_xz_m':[[490,-645],[545,-645],[545,-565],[490,-565]],
        'role':'new_external_headwater_landform','edit_status':'not_applied',
        'candidate_source_ground_y_m':22,'source_ground_currently_m':0,
        'catchment_extent':'not established; this finite patch alone cannot prove supply'})
    graph['finite_candidate_domains']=domains
    graph['source_audit']=audit_source(graph,scene,brief,field)
    graph['structural_check']=validate(graph)
    return graph


def audit_source(graph,scene=None,brief=None,field=None):
    scene=scene or json.loads(SCENE.read_text());brief=brief or json.loads(BRIEF.read_text())
    field=field or terrain.field_from_brief(brief)
    nodes={n['id']:n for n in graph['nodes']}
    road_nodes={n['id']:[n['position_m'][0],n['position_m'][2]] for n in scene['road_nodes']}
    roads=[(r['id'],rectangle(road_nodes[r['from_node']],road_nodes[r['to_node']],r['width_m']))
           for r in scene['roads'] if math.dist(road_nodes[r['from_node']],road_nodes[r['to_node']])>1e-8]
    footprints=[(b['id'],b['source_footprint_xz_m']) for b in scene['instances']]
    result=[]
    for d in graph['finite_candidate_domains']:
        p=d['polygon_xz_m'];xs=[x[0] for x in p];zs=[x[1] for x in p]
        def overlaps(items):
            out=[]
            for id,q in items:
                if max(v[0] for v in q)<min(xs) or min(v[0] for v in q)>max(xs) or max(v[1] for v in q)<min(zs) or min(v[1] for v in q)>max(zs): continue
                overlap=terrain._intersect(p,terrain._inside_planes(terrain._convex(q)))
                if overlap and abs(terrain._area(overlap))>1e-7:
                    out.append({'id':id,'area_m2':round(abs(terrain._area(overlap)),6)})
            return out
        samples=list(p)
        for a,b in zip(p,p[1:]+p[:1]):
            count=max(1,math.ceil(math.dist(a,b)/2))
            samples += [[a[0]+(b[0]-a[0])*i/count,a[1]+(b[1]-a[1])*i/count] for i in range(count+1)]
        h=[field.height(*q) for q in samples]
        result.append({'domain_id':d['id'],'area_m2':round(abs(terrain._area(p)),6),
            'source_h_boundary_min_m':round(min(h),6),'source_h_boundary_max_m':round(max(h),6),
            'building_overlaps':overlaps(footprints),'road_crossings':overlaps(roads),
            'plot_and_courtyard_ownership':'not cleared; land-use worker review required',
            'wall_crossing_status':'new water-gate openings required where this corridor crosses wall; not built'})
    crossings=sorted({x['id'] for r in result for x in r['road_crossings']})
    return {'method':'exact convex polygon intersection against frozen r2 source building footprints and road strips; boundary H samples <=2m spacing, not a terrain-volume analysis',
        'domains':result,'building_overlap_count':sum(len(r['building_overlaps']) for r in result),
        'road_crossing_ids':crossings,'road_crossings_require_bridges_or_covered_flumes':True,
        'domain_area_sum_upper_bound_m2':round(sum(r['area_m2'] for r in result),3),
        'deduplicated_union_area_m2':None,'full_fine_fill_forbidden':True,
        'fine_cell_budget':'not allocated: no full-reservoir/canal .1m fill; count bounded walk/bridge caps after concept choice'}


def validate(graph):
    errors=[];checks=[];ns={n['id']:n for n in graph['nodes']}
    if len(ns)!=len(graph['nodes']):errors.append('duplicate node IDs')
    ids=set()
    for n in graph['nodes']:
        vals=n.get('xz_m',[])+[n.get('reference_y_m')]
        if len(vals)!=3 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in vals):
            errors.append('nonfinite node '+n['id'])
    adjacency={id:[] for id in ns}
    for e in graph['edges']:
        if e['id'] in ids:errors.append('duplicate edge '+e['id'])
        ids.add(e['id'])
        if e['source'] not in ns or e['target'] not in ns:
            errors.append('unknown endpoint '+e['id']);continue
        a,b=ns[e['source']],ns[e['target']];adjacency[a['id']].append(b['id'])
        profile=e['profile_xyz_m'];expected=[[a['xz_m'][0],a['reference_y_m'],a['xz_m'][1]],
                                         [b['xz_m'][0],b['reference_y_m'],b['xz_m'][1]]]
        if len(profile)<2 or profile[0]!=expected[0] or profile[-1]!=expected[1]:errors.append('endpoint/profile mismatch '+e['id'])
        if any(len(p)!=3 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in p) for p in profile):
            errors.append('nonfinite profile '+e['id']);continue
        head=a['reference_y_m']-b['reference_y_m']
        if e['mode'] in GRAVITY:
            if head<=0 or any(q[1]>p[1]+1e-9 for p,q in zip(profile,profile[1:])):
                errors.append('uphill or zero-head gravity edge '+e['id'])
        elif e['mode'] in {'manual_lift','manual_removal'}:
            if not e.get('energy_source') or e.get('gravity_claim') is not False:errors.append('unpowered lift '+e['id'])
        else:errors.append('unknown transport mode '+e['id'])
        if a['network'] in {'storm','contained_waste'} and b['network'].startswith('protected_supply'):
            errors.append('contamination backconnection '+e['id'])
        if a['network']=='industrial_nonpotable' and b['network'].startswith('protected_supply') and a['id']!='NE_INTAKE':
            errors.append('industrial-to-supply connection '+e['id'])
        length=sum(math.hypot(q[0]-p[0],q[2]-p[2]) for p,q in zip(profile,profile[1:]))
        checks.append({'edge_id':e['id'],'head_drop_m':round(head,9),'horizontal_run_m':round(length,6),
                       'mean_head_grade':round(head/length,9) if length else None,
                       'transport_mode':e['mode'],'hydraulically_validated':False})
    # Direct and indirect dirty-water paths to any protected supply are forbidden.
    for start,n in ns.items():
        if n['network'] not in {'storm','contained_waste'}:continue
        todo=list(adjacency[start]);seen=set()
        while todo:
            p=todo.pop()
            if p in seen:continue
            seen.add(p)
            if ns[p]['network'].startswith('protected_supply'):errors.append('dirty path to protected supply from '+start)
            todo.extend(adjacency[p])
    # Global directed graph must remain finite and acyclic; lift energy does not
    # license a perpetual water circuit.
    colors={}
    def visit(p):
        if colors.get(p)==1:errors.append('directed cycle at '+p);return
        if colors.get(p)==2:return
        colors[p]=1
        for q in adjacency[p]:visit(q)
        colors[p]=2
    for p in adjacency:visit(p)
    if graph.get('datum',{}).get('r2_modified') is not False:errors.append('frozen-r2 mutation flag')
    return {'passed':not errors,'errors':sorted(set(errors)),'nodes':len(ns),'edges':len(graph['edges']),
            'edge_checks':checks,'scope':'topology, finite coordinates, declared energy and monotonically downhill profiles only; NOT hydraulic/quality/engineering validation'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');args=p.parse_args()
    g=build_candidate()
    if args.write:CANDIDATE.write_text(json.dumps(g,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({'structural_check':{k:v for k,v in g['structural_check'].items() if k!='edge_checks'},
        'source_audit':{k:v for k,v in g['source_audit'].items() if k!='domains'}},indent=2))
    if not g['structural_check']['passed']:raise SystemExit(1)
if __name__=='__main__':main()
