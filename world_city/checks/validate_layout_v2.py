#!/usr/bin/env python3
"""Read-only checks of a 2D planning draft. Does not validate 3D gameplay."""
from pathlib import Path
import json, math, hashlib, collections, sys
ROOT=Path(__file__).resolve().parents[2]
def distance(p,q):return math.hypot(p[0]-q[0],p[1]-q[1])
def point_segment(p,a,b):
    v=[b[i]-a[i]for i in(0,1)];ll=sum(x*x for x in v)
    if not ll:return distance(p,a)
    t=max(0,min(1,sum((p[i]-a[i])*v[i]for i in(0,1))/ll));return distance(p,[a[i]+t*v[i]for i in(0,1)])
def poly_overlap(a,b):
    for poly in(a,b):
        for i in range(len(poly)):
            p,q=poly[i],poly[(i+1)%len(poly)];axis=[p[1]-q[1],q[0]-p[0]]
            ap=[sum(p[j]*axis[j]for j in(0,1))for p in a];bp=[sum(p[j]*axis[j]for j in(0,1))for p in b]
            if max(ap)<=min(bp)+.001 or max(bp)<=min(ap)+.001:return False
    return True

def validate(d):
    errors=[];warnings=[];checks=[]
    def check(name,ok,detail=None):
        checks.append({'name':name,'passed':bool(ok),'detail':detail})
        if not ok:errors.append(name)
    check('explicit_plan_status',d['status'] in ('draft_layout_v2_visual_review_pending','draft_layout_v2_reviewed_2d')and d['all_quantities_are_planning_values']is True)
    b=d['building_plans'];r=d['roads'];n={n['id']:n for n in d['road_nodes']};rb={r['id']:r for r in r};bb={b['id']:b for b in b};di={x['id']:x for x in d['districts']}
    check('unique_building_ids',len(bb)==len(b));check('unique_road_ids',len(rb)==len(r))
    counts=collections.Counter(x['district_id']for x in b)
    check('district_references',all(i in di for i in counts),dict(counts))
    check('actual_count_report',len(b)==d['counts_report']['building_footprints'] and d['layout_targets_not_constraints'] is True)
    check('area_budget_sum',sum(v['area_budget_ha']for i,v in di.items()if i!='S01')==105 and di['S01']['area_budget_ha']==18)
    check('closed_wall_area_105ha',abs(d['wall_measured_area_ha']-105)<.001)
    check('road_node_references',all(x['from_node']in n and x['to_node']in n for x in r))
    graph=collections.defaultdict(set)
    for road in r:graph[road['from_node']].add(road['to_node']);graph[road['to_node']].add(road['from_node'])
    visited=set();todo=[next(iter(graph))]
    while todo:
        u=todo.pop()
        if u in visited:continue
        visited.add(u);todo.extend(graph[u]-visited)
    check('connected_used_road_graph',len(visited)==len(graph),{'visited':len(visited),'used_nodes':len(graph)})
    check('all_building_road_references',all(x['road_access']['road_id']in rb for x in b))
    boundary_fail=[];roadpoint_fail=[]
    for building in b:
        p=building['footprint_xz_m'];e=building['entrance']['position_xz_m']
        if min(point_segment(e,p[i],p[(i+1)%len(p)])for i in range(len(p)))>.01:boundary_fail.append(building['id'])
        road=rb[building['road_access']['road_id']];a=n[road['from_node']]['position_m'];z=n[road['to_node']]['position_m'];ap=[a[0],a[2]];zp=[z[0],z[2]]
        if point_segment(building['road_access']['connection_xz_m'],ap,zp)>.02:roadpoint_fail.append(building['id'])
    check('entrances_on_footprint_edges',not boundary_fail,boundary_fail[:20]);check('access_points_on_named_roads',not roadpoint_fail,roadpoint_fail[:20])
    # Broad-phase cells followed by convex separating-axis intersection.
    buckets=collections.defaultdict(list);pairs=set();overlaps=[]
    for i,building in enumerate(b):
        p=building['footprint_xz_m'];xs=[x[0]for x in p];zs=[x[1]for x in p]
        keys=[(x,z)for x in range(math.floor(min(xs)/40),math.floor(max(xs)/40)+1)for z in range(math.floor(min(zs)/40),math.floor(max(zs)/40)+1)]
        for key in keys:
            for j in buckets[key]:
                if (j,i)in pairs:continue
                pairs.add((j,i))
                if poly_overlap(p,b[j]['footprint_xz_m']):overlaps.append([b[j]['id'],building['id']])
            buckets[key].append(i)
    check('no_building_footprint_overlaps',not overlaps,overlaps[:25])
    roadpolys=[]
    for road in r:
        a=n[road['from_node']]['position_m'];z=n[road['to_node']]['position_m'];a=[a[0],a[2]];z=[z[0],z[2]];L=distance(a,z);ux,uz=(z[0]-a[0])/L,(z[1]-a[1])/L;w=road['width_m']/2
        roadpolys.append((road,[[a[0]-uz*w,a[1]+ux*w],[z[0]-uz*w,z[1]+ux*w],[z[0]+uz*w,z[1]-ux*w],[a[0]+uz*w,a[1]-ux*w]]))
    crossings=[]
    for building in b:
        if building['district_id']=='D09':continue # Gate openings and wall stairs are explicit later 3D checks.
        for road,p in roadpolys:
            if road['kind']=='wall_walk':continue
            if poly_overlap(building['footprint_xz_m'],p):crossings.append([building['id'],road['id']])
    check('no_ordinary_building_road_overlaps',not crossings,crossings[:25])
    check('functional_flow_endpoints',all(x['from_building']in bb and x['to_building']in bb for x in d['functional_links']))
    check('implementation_tiers',all(x['implementation_tier']in('active_gameplay','exterior_only','interior_selected')for x in b))
    check('no_claimed_built_geometry',not d['asset_placements'] and not d['terrain_patches'] and all(x['status']=='planned_not_built'for x in b))
    refs=[d['source_references']['concept']]+d['source_references']['assets']+d['source_references']['framework'];bad=[]
    for ref in refs:
        p=ROOT/ref['path']
        if not p.exists()or hashlib.sha256(p.read_bytes()).hexdigest()!=ref['sha256']:bad.append(ref['path'])
    check('source_reference_hashes',not bad,bad)
    courtyard_conflicts=[]
    for plot in d['plots']:
        if not plot.get('courtyard_xz_m'):continue
        for building in b:
            if poly_overlap(plot['courtyard_xz_m'],building['footprint_xz_m']):courtyard_conflicts.append([plot['id'],building['id']])
    check('courtyards_unbuilt',not courtyard_conflicts,courtyard_conflicts[:20])
    check('shared_passage_parents',all(x['road_access'].get('passage_via_building') in bb for x in b if x['road_access']['mode']=='via_shared_plot_passage'))
    check('required_south_bridge_route',any(x['id']=='RT_BRIDGE' and x['kind']=='bridge'for x in d['street_routes']))
    check('two_explicit_water_posterns',len([x for x in d['site_features']if x['kind']=='water_postern'])==2)
    check('road_heights_explicitly_unresolved',all(x['position_m'][1] is None for x in d['road_nodes']))
    tiers=dict(collections.Counter(x['implementation_tier']for x in b))
    warnings=['3D road grades, door clearances, ramps and cart turns have not been tested.','8 well reservations have a clear 2D center only; public access, water quality, setbacks and pipe profiles remain unverified.','SVG/HTML are planning maps, not rendered voxel geometry.','Coarse/fine chunk seams and mixed-pitch streaming are contract proposals, not implemented capabilities.']
    return {'passed':not errors,'checks':checks,'failure_count':len(errors),'errors':errors,'warnings':warnings,'building_tiers':tiers,'building_count':len(b),'road_count':len(r),'scope':'2D plan consistency and references only'}
if __name__=='__main__':
    d=json.loads((ROOT/'world_city/data/city_brief.v2.json').read_text());result=validate(d)
    out=ROOT/'world_city/checks/validation_v2.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['passed']else 1)
