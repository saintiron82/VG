"""Bounded landscape source recipes. No scene placement, mesh or cell mutation."""
from __future__ import annotations
import copy, json, math, random
from collections import Counter
from pathlib import Path
from world_city.runtime_city.urban_fabric.revisions.r3.author_overlay import TREE_FORMS, make_master, master_bounds
from world_city.runtime_city.urban_fabric.author import rect, digest
from world_city.runtime_city.checks.placement import polygon_area, road_ribbon, _SpatialIndex
HERE = Path(__file__).parent
KINDS = ('outside_woodland', 'productive_orchard', 'public_park', 'monastery_garden', 'clergy_garden', 'estate_garden')


def _cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def _on(p,a,b): return abs(_cross(a,b,p))<1e-7 and min(a[0],b[0])-1e-7<=p[0]<=max(a[0],b[0])+1e-7 and min(a[1],b[1])-1e-7<=p[1]<=max(a[1],b[1])+1e-7

def inside(p, poly, boundary=True):
    hit=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if _on(p,a,b): return boundary
        if (a[1]>p[1]) != (b[1]>p[1]) and p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]: hit=not hit
    return hit


def _crosses(a,b,c,d): return _cross(a,b,c)*_cross(a,b,d)<-1e-10 and _cross(c,d,a)*_cross(c,d,b)<-1e-10

def overlaps(a,b):
    if any(_crosses(x,y,u,v) for x,y in zip(a,a[1:]+a[:1]) for u,v in zip(b,b[1:]+b[:1])): return True
    if any(inside(p,b,False) for p in a) or any(inside(p,a,False) for p in b): return True
    # Coincident polygon boundaries need an interior witness, too.
    return inside([sum(p[0] for p in a)/len(a),sum(p[1] for p in a)/len(a)],b,False) or inside([sum(p[0] for p in b)/len(b),sum(p[1] for p in b)/len(b)],a,False)


def contains(outer,inner):
    return all(inside(p,outer) for p in inner) and not any(_crosses(x,y,u,v) for x,y in zip(outer,outer[1:]+outer[:1]) for u,v in zip(inner,inner[1:]+inner[:1]))


def _edge_distance(p,poly):
    ans=float('inf')
    for a,b in zip(poly,poly[1:]+poly[:1]):
        dx,dz=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dz)/(dx*dx+dz*dz)))
        ans=min(ans,math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dz))
    return ans


def source_key(spec): return 'uf_r3_'+spec['kind']+'_'+digest(spec)[:14]
def make_asset_master(spec): return make_master(spec) # Frozen shared source, including original cache ID.
def resource_for(spec): return {'pitch':1 if spec['kind'] in ('forest_tree','understory') else .5}
def _point(p,origin,yaw): return [origin[0]+math.cos(yaw)*p[0]+math.sin(yaw)*p[1],origin[1]-math.sin(yaw)*p[0]+math.cos(yaw)*p[1]]


def build_landscape_recipe(site, wall_polygon_xz_m, exclusions=(), property_recipe=None):
    """Source-only bounded recipe against explicit ground polygons and clearances.

    site: id, landscape_kind, polygon_xz_m or polygons_xz_m. Exclusions contain
    id and polygon_xz_m. Existing path ribbons belong in exclusions. Formal
    gardens require width_m/depth_m/origin_xz_m/yaw_rad buildable frame.
    """
    site=copy.deepcopy(site);kind=site['landscape_kind'];sid=site['id']
    if kind not in KINDS: raise ValueError('Unknown landscape kind')
    if kind=='estate_garden':
        if not property_recipe or property_recipe['property_type']!='noble_estate': raise ValueError('Estate garden must bind to an existing noble property recipe')
        items=[p for p in property_recipe['placements'] if p['role'].startswith(('garden_bed','orchard_tree'))]
        return {'schema':'riverstone.concept_city.landscape_recipe.v1','site':site,'placements':[], 'existing_owner_bindings':[p['id'] for p in items], 'master_specs':{},'land_use_regions':[r for r in property_recipe['ground_regions'] if 'garden' in r['land_use'] or 'orchard' in r['land_use']], 'access_reservations':[r for r in property_recipe['entrance_routes'] if r.get('kind')=='garden_service_walk'], 'floor_owner':property_recipe['surface_ownership']['owner_placement_id'],'policy':'Reuse the estate garden already owned by the property recipe; do not place duplicate foliage or floors.', 'checks':{'valid':True,'errors':[]},'no_citywide_placement':True}
    patches=site.get('polygons_xz_m') or [site['polygon_xz_m']]
    if not patches or any(len(p)<3 or polygon_area(p)<=0 for p in patches): raise ValueError('Landscape requires nonempty bounded polygons')
    if kind=='productive_orchard' and not site.get('productive_ground',False): raise ValueError('Orchard rows require explicitly productive ground')
    if kind=='outside_woodland' and any(overlaps(p,wall_polygon_xz_m) for p in patches): raise ValueError('Outside woodland patch intersects the walled city')
    if kind!='outside_woodland' and any(not contains(wall_polygon_xz_m,p) for p in patches): raise ValueError('Urban garden or park must lie inside the city wall')
    exclusion_records=copy.deepcopy(list(exclusions));routes=[];regions=[];placements=[];specs={};errors=[]
    if kind=='outside_woodland':
        for i,(a,b) in enumerate(zip(wall_polygon_xz_m,wall_polygon_xz_m[1:]+wall_polygon_xz_m[:1])):
            exclusion_records.append({'id':'wall_standoff:'+str(i),'polygon_xz_m':road_ribbon(a,b,24),'reason':'12 m outside-wall canopy clearance'})
            exclusion_records.append({'id':'wall_corner_standoff:'+str(i),'polygon_xz_m':rect(a,24,24),'reason':'conservative 12 m wall-corner clearance'})
    xs=[p[0] for patch in patches for p in patch];zs=[p[1] for patch in patches for p in patch];xmin,xmax,zmin,zmax=min(xs),max(xs),min(zs),max(zs);area=sum(polygon_area(p) for p in patches)
    origin=site.get('origin_xz_m',[(xmin+xmax)/2,(zmin+zmax)/2]);yaw=site.get('yaw_rad',0);w=site.get('width_m',xmax-xmin);d=site.get('depth_m',zmax-zmin)
    rng=random.Random(int(digest([sid,kind,site.get('seed',0)])[:16],16));taken=[];clusters=[];clearings=[]
    def fits(poly):
        return any(contains(p,poly) for p in patches) and not any(overlaps(poly,e['polygon_xz_m']) for e in exclusion_records)
    def add_route(label,points,width):
        ribbons=[road_ribbon(a,b,width) for a,b in zip(points,points[1:]) if math.dist(a,b)>.001]
        if not all(any(contains(p,r) for p in patches) for r in ribbons): raise ValueError('Designed garden path leaves its reserved ground')
        route={'id':sid+':'+label,'polyline_xz_m':points,'width_m':width,'ribbon_polygons_xz_m':ribbons,'external_connection_status':'requires_landuse_entry_link'};routes.append(route)
        exclusion_records.extend({'id':route['id']+':'+str(i),'polygon_xz_m':r} for i,r in enumerate(ribbons))
    def place(spec,p,theta,role,collision=True):
        bw,bd,bh=master_bounds(spec);poly=rect(p,bw,bd,theta)
        if not fits(poly): return None
        is_tree=spec['kind']=='forest_tree';root=rect(p,2,2,theta) if is_tree else poly
        if is_tree and any(math.dist(p,q)<(4.5 if kind=='outside_woodland' else 6) for q in taken): return None
        if is_tree: taken.append(p)
        key=source_key(spec);specs[key]=spec;idx=len(placements)
        item={'id':sid+':'+role+':'+str(idx).zfill(4),'source_ground_id':sid,'role':role,'asset_key':key,'spec':spec,'position_m':[p[0],site.get('datum_y_m',0),p[1]],'yaw_rad':theta,'footprint_xz_m':poly,'collision_footprint_xz_m':root,'collision_enabled':collision,'collision_policy':'trunk_root_only' if is_tree else 'solid' if collision else 'soft_understory','ground_anchor':{'policy':'project_y_only_sample_roots_or_base','sample_center_xz_m':p,'support_points_xz_m':root,'support_footprint_kind':'trunk_root' if is_tree else 'short_module_base','datum_y_m':site.get('datum_y_m',0),'preserve_xz':True,'footing_embed_m':1 if is_tree else .5,'maximum_support_height_delta_m':.75,'exceedance_action':'report_or_author_ground_step; never_scale_crown'},'intentional_foliage_overlap_group':sid+':foliage' if spec['kind'] in ('forest_tree','understory') else None}
        placements.append(item);return item
    if kind in ('outside_woodland','public_park'):
        forest=kind=='outside_woodland';target=min(site.get('maximum_trees',400 if forest else 36),int(area/(115 if forest else 650)))
        # Clusters are actual random points, not a jittered planting lattice.
        for _ in range(max(4,int(area/(3500 if forest else 4500)))):
            for attempt in range(200):
                p=[rng.uniform(xmin,xmax),rng.uniform(zmin,zmax)]
                if any(inside(p,q) for q in patches): clusters.append([*p,rng.uniform(12,25),rng.uniform(13,30)]);break
        def clearing(p):
            if forest:
                mid=xmin+(xmax-xmin)*.53+math.sin((p[1]-zmin)/max(1,zmax-zmin)*math.pi*2)*min(18,(xmax-xmin)*.13)
                return abs(p[0]-mid)<4 and zmin+14<p[1]<zmax-14
            return ((p[0]-(xmin+xmax)/2)/max(1,w*.31))**2+((p[1]-(zmin+zmax)/2)/max(1,d*.32))**2<1
        if forest:
            pts=[[xmin+(xmax-xmin)*.53+math.sin(t*math.pi*2)*min(18,(xmax-xmin)*.13),zmin+t*(zmax-zmin)] for t in (.12,.22,.32,.42,.52,.62,.72,.82,.88)]
            clearings.append({'kind':'winding_open_ground_gap','centerline_xz_m':pts,'nominal_width_m':8,'surface_owner':'existing_ground'})
            exclusion_records.extend({'id':sid+':clearing:'+str(i),'polygon_xz_m':road_ribbon(a,b,8)} for i,(a,b) in enumerate(zip(pts,pts[1:])))
        else:
            lawn=[[(xmin+xmax)/2+math.cos(j*math.tau/24)*w*.31,(zmin+zmax)/2+math.sin(j*math.tau/24)*d*.32] for j in range(24)]
            clearings.append({'kind':'central_open_lawn','polygon_xz_m':lawn,'surface_owner':'existing_ground'})
            exclusion_records.append({'id':sid+':open_lawn','polygon_xz_m':lawn})
            for route in site.get('park_walks',[]):add_route(route['id'],route['polyline_xz_m'],route.get('width_m',3))
        forms=list(TREE_FORMS) if forest else ['broad_oak','spreading_elm','low_hazel'];attempts=0
        while len(taken)<target and attempts<max(100,target*100):
            attempts+=1;c=rng.choice(clusters)
            p=[rng.gauss(c[0],c[2]),rng.gauss(c[1],c[3])] if rng.random()<.8 else [rng.uniform(xmin,xmax),rng.uniform(zmin,zmax)]
            if clearing(p): continue
            containing=[q for q in patches if inside(p,q)]
            if not containing:continue
            edge=max(_edge_distance(p,q) for q in containing)
            if forest and rng.random()>min(1,max(0,(edge-3)/14)):continue
            form=rng.choice(forms);place({'kind':'forest_tree','form':form},p,rng.uniform(-math.pi,math.pi),'woodland_tree' if forest else 'park_grove_tree')
        if forest:
            for j in range(int(len(taken)*.55)):
                q=rng.choice(taken);angle=rng.random()*math.tau;p=[q[0]+math.cos(angle)*rng.uniform(3,5),q[1]+math.sin(angle)*rng.uniform(3,5)]
                if not clearing(p):place({'kind':'understory','width_m':4,'depth_m':4,'height_m':2.5},p,rng.uniform(-math.pi,math.pi),'woodland_understory',False)
        if target and len(taken)<target*.6:errors.append({'check':'underfilled_bounded_recipe','accepted_trees':len(taken),'target_trees':target,'action':'review_site_or_clearances; do_not_force_fill'})
    else:
        # Functional frame is deliberate; rows are restricted to productive grounds.
        frame=[_point(p,origin,yaw) for p in rect([0,0],w,d)]
        if not any(contains(p,frame) for p in patches):raise ValueError('Formal productive garden frame must fit one reserved polygon')
        if kind=='productive_orchard':
            for x in range(math.ceil((-w/2+5)/10)*10,math.floor((w/2-5)/10)*10+1,10):
                for z in range(math.ceil((-d/2+5)/10)*10,math.floor((d/2-5)/10)*10+1,10):place({'kind':'forest_tree','form':'low_hazel'},_point([x,z],origin,yaw),yaw,'productive_orchard_tree')
            regions.append({'id':sid+':orchard','land_use':'productive_orchard_rows','polygon_xz_m':frame,'surface_owner':'existing_ground'})
        else:
            if w<40 or d<40:raise ValueError('Formal monastery/clergy garden needs a 40 m buildable frame')
            add_route('central_walk',[_point([0,-d/2+2],origin,yaw),_point([0,d/2-2],origin,yaw)],2)
            add_route('cross_walk',[_point([-w/2+2,0],origin,yaw),_point([w/2-2,0],origin,yaw)],2)
            xs=(-12,-4,4,12) if kind=='monastery_garden' else (-9,9)
            zs=(-9,9) if kind=='monastery_garden' else (-8,8)
            for x in xs:
                for z in zs:place({'kind':'garden_bed','width_m':6,'depth_m':3,'height_m':1.5},_point([x,z],origin,yaw),yaw,'herb_kitchen_bed' if kind=='monastery_garden' else 'quiet_formal_bed')
            for sign in (-1,1):
                for x in (-w/2+6,w/2-6):place({'kind':'forest_tree','form':'low_hazel' if kind=='monastery_garden' else 'leaning_ash'},_point([x,sign*(d/2-6)],origin,yaw),yaw,'garden_orchard_tree' if kind=='monastery_garden' else 'clergy_shade_tree')
            regions.append({'id':sid+':productive_garden' if kind=='monastery_garden' else sid+':quiet_garden','land_use':'monastery_herb_kitchen_and_small_orchard' if kind=='monastery_garden' else 'clergy_quiet_formal_close','polygon_xz_m':frame,'surface_owner':'existing_ground'})
    result={'schema':'riverstone.concept_city.landscape_recipe.v1','site':site,'wall_polygon_xz_m':wall_polygon_xz_m,'placements':placements,'master_specs':specs,'access_reservations':routes,'land_use_regions':regions,'clearings':clearings,'cluster_centers_xz_spread_m':clusters,'exclusions':exclusion_records,'source_errors':errors,'surface_ownership':'No additional floor planes. Paint path/bed-ground regions into the existing exclusive ground owner. Raised beds are actual solids.','no_citywide_placement':True,'compile_budget':{'unique_master_count':len(specs),'existing_frozen_r3_master_sources':True,'max_candidates_per_master':10000,'max_output_cells_per_master':5000},'sampling_resource_by_asset':{k:resource_for(s) for k,s in specs.items()}}
    result['metrics']=measure(result);result['checks']=validate_recipe(result);return result


def measure(recipe):
    trees=[p for p in recipe['placements'] if p['spec']['kind']=='forest_tree'];site=recipe['site'];patches=site.get('polygons_xz_m') or [site['polygon_xz_m']];area=sum(polygon_area(p) for p in patches);index=_SpatialIndex(16)
    for j,p in enumerate(trees): index.add(str(j),p['footprint_xz_m'])
    samples=[];covered=0;total=0
    for patch in patches:
        for x in range(math.ceil(min(p[0] for p in patch)),math.floor(max(p[0] for p in patch)),2):
            for z in range(math.ceil(min(p[1] for p in patch)),math.floor(max(p[1] for p in patch)),2):
                q=[x+1,z+1]
                if not inside(q,patch): continue
                total+=1;hit=False
                for key in index.candidates(rect(q,.1,.1)):
                    tree=trees[int(key)];theta=tree['yaw_rad'];dx,dz=q[0]-tree['position_m'][0],q[1]-tree['position_m'][2];lx,lz=math.cos(theta)*dx-math.sin(theta)*dz,math.sin(theta)*dx+math.cos(theta)*dz
                    if any((lx-a)**2+(lz-c)**2<=r*r for a,b,c,r,h in TREE_FORMS[tree['spec']['form']]['lobes']):hit=True;break
                covered+=hit;samples.append((q,hit))
    nearest=[min(math.dist([p['position_m'][0],p['position_m'][2]],[q['position_m'][0],q['position_m'][2]]) for q in trees if q is not p) for p in trees] if len(trees)>1 else []
    mean=sum(nearest)/len(nearest) if nearest else 0;cv=(sum((n-mean)**2 for n in nearest)/len(nearest))**.5/mean if mean else 0
    cores=[]
    for cx,cz,*_ in recipe['cluster_centers_xz_spread_m']:
        subset=[hit for q,hit in samples if abs(q[0]-cx)<=20 and abs(q[1]-cz)<=20]
        if subset:cores.append({'center_xz_m':[cx,cz],'window_m':40,'rounded_canopy_fraction':sum(subset)/len(subset)})
    return {'ground_area_m2':area,'trees':len(trees),'understory':sum(p['spec']['kind']=='understory' for p in recipe['placements']),'tree_forms':dict(Counter(p['spec']['form'] for p in trees)),'actual_geometry_height_range_m':[min((TREE_FORMS[p['spec']['form']]['height_m'] for p in trees),default=0),max((TREE_FORMS[p['spec']['form']]['height_m'] for p in trees),default=0)],'rounded_crown_projection_union_fraction_2m_samples':covered/total if total else 0,'measurement':'Union of horizontal rounded-lobe projections, sampled on a 2 m grid; not exact sampled foliage or a sum of overlapping crown areas.','wooded_core_windows':cores,'nearest_trunk_spacing_mean_m':mean,'nearest_trunk_spacing_cv':cv}


def validate_recipe(recipe):
    if recipe['site']['landscape_kind']=='estate_garden':return recipe['checks']
    errors=list(recipe['source_errors']);site=recipe['site'];patches=site.get('polygons_xz_m') or [site['polygon_xz_m']];forest=site['landscape_kind']=='outside_woodland';trees=[]
    for p in recipe['placements']:
        poly=p['footprint_xz_m'];pos=[p['position_m'][0],p['position_m'][2]];w,d,h=master_bounds(p['spec']);expected=rect(pos,w,d,p['yaw_rad'])
        if any(math.dist(a,b)>1e-5 for a,b in zip(poly,expected)):errors.append({'check':'stale_footprint','id':p['id']})
        if not any(contains(q,poly) for q in patches):errors.append({'check':'outside_ground','id':p['id']})
        if any(overlaps(poly,e['polygon_xz_m']) for e in recipe['exclusions']):errors.append({'check':'reserved_access_or_building_overlap','id':p['id']})
        if forest and overlaps(poly,recipe['wall_polygon_xz_m']):errors.append({'check':'urban_forest_forbidden','id':p['id']})
        if not forest and not contains(recipe['wall_polygon_xz_m'],poly):errors.append({'check':'garden_outside_wall','id':p['id']})
        if p['spec']['kind']=='forest_tree':
            trees.append(p)
            if polygon_area(p['ground_anchor']['support_points_xz_m'])>4.001:errors.append({'check':'canopy_used_as_root_support','id':p['id']})
    solids=[p for p in recipe['placements'] if p['collision_enabled']]
    for i,p in enumerate(solids):
        for q in solids[:i]:
            if overlaps(p['collision_footprint_xz_m'],q['collision_footprint_xz_m']):errors.append({'check':'root_or_solid_collision','ids':[p['id'],q['id']]})
    if forest and len(trees)>=30:
        if len(recipe['metrics']['tree_forms'])<5:errors.append({'check':'insufficient_crown_geometry_variety'})
        if recipe['metrics']['nearest_trunk_spacing_cv']<.15:errors.append({'check':'uniform_plantation_spacing'})
        if max((c['rounded_canopy_fraction'] for c in recipe['metrics']['wooded_core_windows']),default=0)<.4:errors.append({'check':'no_visibly_wooded_core'})
    return {'valid':not errors,'errors':errors,'scope':'bounded source recipe and exclusion checks; terrain/root projection and actual city visual review remain external'}


def examples(wall):
    return [
        {'id':'FIXTURE_OUTSIDE_NW','landscape_kind':'outside_woodland','polygon_xz_m':[[-660,-310],[-515,-325],[-500,-230],[-530,-170],[-655,-185]],'maximum_trees':120},
        {'id':'FIXTURE_PARK','landscape_kind':'public_park','polygon_xz_m':rect([0,0],80,64),'park_walks':[{'id':'promenade','polyline_xz_m':[[-38,0],[0,5],[38,0]],'width_m':3}]},
        {'id':'FIXTURE_ORCHARD','landscape_kind':'productive_orchard','polygon_xz_m':rect([0,0],44,44),'width_m':44,'depth_m':44,'productive_ground':True},
        {'id':'FIXTURE_MONASTERY','landscape_kind':'monastery_garden','polygon_xz_m':rect([0,0],44,44),'width_m':44,'depth_m':44},
        {'id':'FIXTURE_CLERGY','landscape_kind':'clergy_garden','polygon_xz_m':rect([0,0],44,44),'width_m':44,'depth_m':44},
    ]


def main():
    path=Path('world_city/concept_city_v3/source/plan.json');plan=json.loads(path.read_text());wall=plan['boundary_xz_m'];out=HERE/'generated';out.mkdir(exist_ok=True);summary={}
    for site in examples(wall):
        r=build_landscape_recipe(site,wall);(out/(site['landscape_kind']+'.recipe.json')).write_text(json.dumps(r,separators=(',',':'))+'\n');summary[site['landscape_kind']]={'metrics':r['metrics'],'checks':r['checks'],'placements':len(r['placements']),'shared_sources':len(r['master_specs'])}
    (out/'summary.json').write_text(json.dumps({'status':'bounded_api_fixtures_not_citywide_landscape_placement','wall_source':str(path),'wall_polygon_sha256':digest(wall),'recipes':summary},indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
